"""`services/dispatch.apply_price_bump` uchun testlar.

Baza va RabbitMQ kerak emas: DB sessiyasi soxta obyekt bilan, narx tekshiruvi va
navbatga qo'yish esa monkeypatch bilan almashtiriladi. Tekshirilayotgani —
apply_price_bump ning QAROR mantiqi: qachon rad etadi, buyurtmani qanday holatga
qaytaradi va qidiruvni haqiqatan navbatga qo'yadimi.

Ishga tushirish: `pytest tests/`
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from order.models import Order, OrderStatus
from services import dispatch as dispatch_service
from services import pricing


class FakeSession:
    """`apply_price_bump` ishlatadigan AsyncSession usullarining minimal o'rnini bosuvchi."""

    def __init__(self) -> None:
        self.commits = 0
        self.statements: list[object] = []

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj, attribute_names=None) -> None:
        # Haqiqiy sessiya qiymatlarni bazadan qayta o'qiydi; bu yerda obyekt
        # allaqachon xotirada yangilangan, shuning uchun hech narsa qilinmaydi.
        return None

    async def execute(self, statement):
        self.statements.append(statement)
        return None


def make_order(**overrides) -> Order:
    """Bazaga tegmasdan, faqat kerakli maydonlari to'ldirilgan Order obyekti."""
    order = Order()
    order.id = 1
    order.customer_id = 100
    order.driver_id = None
    order.cargo_name = "Test yuk"
    order.price = Decimal("500000.00")
    order.base_price = Decimal("500000.00")
    order.original_price = None
    order.currency = "UZS"
    order.status = OrderStatus.PENDING
    order.dispatch_round = 1
    order.price_bump_count = 0
    order.price_bump_requested_at = datetime.now(timezone.utc)
    for key, value in overrides.items():
        setattr(order, key, value)
    return order


@pytest.fixture
def patched(monkeypatch):
    """Narx validatsiyasi (DB sozlamasi) va navbat (RabbitMQ) o'rniga soxta funksiyalar."""
    published: list[tuple[int, str]] = []

    async def fake_validate(db, custom_price, base_price):
        return Decimal(str(custom_price))

    async def fake_publish(order_id, reason, **kwargs):
        published.append((order_id, reason))

    monkeypatch.setattr(
        dispatch_service.pricing, "validate_custom_price_for_db", fake_validate
    )
    monkeypatch.setattr(dispatch_service.queue, "publish_dispatch_job", fake_publish)
    return published


# ────────────────────────────────────────────────────────────
#  1. Regressiya: taklif tushgan, lekin raundlar tugamagan holat
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bump_works_when_no_driver_found_on_first_round(patched):
    """Nomzod umuman topilmasa taklif 1-raundda chiqadi — tugma ishlashi SHART.

    Ilgari shart `dispatch_round >= MAX_ROUNDS` edi va aynan shu holatda 409
    qaytarardi: foydalanuvchi taklifni ko'rardi-yu, bosganda xato olardi.
    """
    order = make_order(dispatch_round=1)
    db = FakeSession()

    result = await dispatch_service.apply_price_bump(db, order, Decimal("600000"))

    assert result.price == Decimal("600000")
    assert patched == [(1, "price_bump")]


@pytest.mark.asyncio
async def test_bump_rejected_when_not_offered(patched):
    order = make_order(price_bump_requested_at=None, dispatch_round=5)
    db = FakeSession()

    with pytest.raises(dispatch_service.DispatchError) as exc:
        await dispatch_service.apply_price_bump(db, order, Decimal("600000"))

    assert exc.value.status_code == 409
    assert patched == []


# ────────────────────────────────────────────────────────────
#  2. Bump'dan keyingi holat
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bump_resets_order_to_searching_state(patched):
    order = make_order(dispatch_round=5, price=Decimal("500000.00"))
    db = FakeSession()

    await dispatch_service.apply_price_bump(db, order, Decimal("700000"))

    assert order.price == Decimal("700000")
    # Asl narx tarix uchun saqlanadi (faqat birinchi bump'da to'ldiriladi)
    assert order.original_price == Decimal("500000.00")
    assert order.dispatch_round == 0
    assert order.price_bump_count == 1
    assert order.price_bump_requested_at is None
    assert order.status == OrderStatus.PENDING


@pytest.mark.asyncio
async def test_original_price_kept_across_repeated_bumps(patched):
    order = make_order(
        price=Decimal("600000.00"), original_price=Decimal("500000.00"), price_bump_count=1
    )
    db = FakeSession()

    await dispatch_service.apply_price_bump(db, order, Decimal("700000"))

    assert order.original_price == Decimal("500000.00")
    assert order.price_bump_count == 2


# ────────────────────────────────────────────────────────────
#  3. Chegaralar
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bump_limit_enforced(patched):
    order = make_order(price_bump_count=dispatch_service.MAX_PRICE_BUMPS)
    db = FakeSession()

    with pytest.raises(dispatch_service.DispatchError) as exc:
        await dispatch_service.apply_price_bump(db, order, Decimal("900000"))

    assert exc.value.status_code == 409
    assert patched == []


@pytest.mark.asyncio
async def test_bump_rejected_when_driver_assigned(patched):
    order = make_order(driver_id=7, status=OrderStatus.ACCEPTED)
    db = FakeSession()

    with pytest.raises(dispatch_service.DispatchError):
        await dispatch_service.apply_price_bump(db, order, Decimal("600000"))

    assert patched == []


@pytest.mark.asyncio
async def test_bump_rejected_on_cancelled_order(patched):
    """Mijoz narx oshirish o'rniga buyurtmani bekor qilgan holat.

    Botdagi eski xabar tugmalari hali ekranda qolgan bo'lishi mumkin — bosilsa
    bekor qilingan buyurtma qayta qidiruvga tushib ketmasligi kerak.
    """
    order = make_order(status=OrderStatus.CANCELLED)
    db = FakeSession()

    with pytest.raises(dispatch_service.DispatchError) as exc:
        await dispatch_service.apply_price_bump(db, order, Decimal("600000"))

    assert exc.value.status_code == 409
    assert patched == []


# ────────────────────────────────────────────────────────────
#  5. "Haydovchi topilmadi" xabarining tugmalari
# ────────────────────────────────────────────────────────────

def _callback_data(keyboard) -> list[str]:
    return [btn["callback_data"] for row in keyboard["inline_keyboard"] for btn in row]


def test_price_bump_keyboard_offers_cancel_as_last_row():
    """Narx oshirish yagona chiqish bo'lmasligi kerak — voz kechish yo'li ham bor."""
    order = make_order(price=Decimal("500000.00"))

    keyboard = dispatch_service.price_bump_keyboard(order)
    rows = keyboard["inline_keyboard"]

    assert rows[-1] == [{"text": "❌ Buyurtmani bekor qilish", "callback_data": "ordercancel:1"}]
    # Qolgan qatorlar — narx variantlari (services/pricing.py QUICK_PRICE_INCREMENTS)
    assert all(data.startswith("pricebump:1:") for data in _callback_data(keyboard)[:-1])
    assert len(rows) == len(pricing.QUICK_PRICE_INCREMENTS) + 1


# ────────────────────────────────────────────────────────────
#  6. Bekor qilishda haydovchining taklif xabari
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pending_offer_lookup_skipped_when_driver_assigned():
    """Haydovchi biriktirilgan bo'lsa taklif xabari qidirilmaydi (DB so'rovi ham yo'q).

    Bu holatda `order/router.py` boshqa yo'ldan boradi — biriktirilgan haydovchiga
    to'liq bildirishnoma yuboriladi.
    """
    order = make_order(driver_id=7, status=OrderStatus.ACCEPTED)
    db = FakeSession()

    assert await dispatch_service.get_pending_offer_message(db, order) is None
    assert db.statements == []


@pytest.mark.asyncio
async def test_notify_offer_cancelled_is_noop_without_offer(monkeypatch):
    """Ochiq taklif bo'lmasa hech kimga xabar yuborilmaydi."""
    calls = []

    async def fake_edit(chat_id, message_id, text):
        calls.append((chat_id, message_id, text))

    monkeypatch.setattr(dispatch_service.notifications, "edit_telegram_message", fake_edit)

    await dispatch_service.notify_offer_cancelled(None)
    assert calls == []

    await dispatch_service.notify_offer_cancelled((555, 42))
    assert calls == [(555, 42, "Bu buyurtma bekor qilindi")]


# ────────────────────────────────────────────────────────────
#  4. Navbat ishlamayotgan holat
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bump_succeeds_when_broker_is_down(monkeypatch):
    """Broker o'chgan bo'lsa ham narx yangilanadi — so'rov 5xx bermaydi.

    Bunday buyurtmani worker'dagi `requeue_stuck_orders` keyinroq qidiruvga qaytaradi.
    """
    async def fake_validate(db, custom_price, base_price):
        return Decimal(str(custom_price))

    async def failing_publish(order_id, reason, **kwargs):
        raise dispatch_service.queue.QueueUnavailable("broker o'chiq")

    monkeypatch.setattr(
        dispatch_service.pricing, "validate_custom_price_for_db", fake_validate
    )
    monkeypatch.setattr(dispatch_service.queue, "publish_dispatch_job", failing_publish)

    order = make_order()
    db = FakeSession()

    result = await dispatch_service.apply_price_bump(db, order, Decimal("600000"))

    assert result.price == Decimal("600000")
    assert result.status == OrderStatus.PENDING
