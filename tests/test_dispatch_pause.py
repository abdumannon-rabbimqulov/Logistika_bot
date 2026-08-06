"""Qidiruvni to'xtatish va narx tahririni cheklash.

Muammo: sender haydovchining telefonida 60 soniyalik taklif ochiq turganda ham narxni
o'zgartira olardi. Haydovchining kartasidagi narx esa yuborilgan paytdagi holicha
qolardi (`_offer_text`) — u eski narxni ko'rib qabul qilardi.

Yechim ikki qismli: (1) narx faqat qidiruv haqiqatan to'xtaganda o'zgaradi,
(2) senderda qidiruvni qo'lda to'xtatish/davom ettirish boshqaruvi bor.

Baza va RabbitMQ kerak emas — `tests/test_dispatch_price_bump.py` dagi kabi soxta
sessiya va monkeypatch ishlatiladi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from order.dispatch_models import DispatchAttempt, DispatchAttemptStatus
from order.models import Order, OrderStatus
from services import dispatch as dispatch_service


class FakeSession:
    """`pause/resume/ensure_price_editable` ishlatadigan usullarning minimal o'rni."""

    def __init__(self) -> None:
        self.commits = 0
        self.statements: list[object] = []

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj, attribute_names=None) -> None:
        return None

    async def execute(self, statement):
        self.statements.append(statement)
        return None


def make_order(**overrides) -> Order:
    """Qidiruvi KETAYOTGAN buyurtma (1-raund yuborilgan) — standart holat."""
    order = Order()
    order.id = 1
    order.customer_id = 100
    order.driver_id = None
    order.cargo_name = "Test yuk"
    order.price = Decimal("500000.00")
    order.status = OrderStatus.PENDING
    order.dispatch_round = 1
    order.last_dispatch_enqueued_at = datetime.now(timezone.utc)
    order.price_bump_requested_at = None
    order.dispatch_paused_at = None
    for key, value in overrides.items():
        setattr(order, key, value)
    return order


def make_attempt(seconds_left: int = 42) -> DispatchAttempt:
    attempt = DispatchAttempt()
    attempt.id = 7
    attempt.order_id = 1
    attempt.status = DispatchAttemptStatus.PENDING
    attempt.expires_at = datetime.now(timezone.utc) + timedelta(seconds=seconds_left)
    return attempt


@pytest.fixture
def no_live_attempt(monkeypatch):
    async def fake(db, order_id):
        return None

    monkeypatch.setattr(dispatch_service, "_live_attempt", fake)


@pytest.fixture
def live_attempt(monkeypatch):
    attempt = make_attempt()

    async def fake(db, order_id):
        return attempt

    monkeypatch.setattr(dispatch_service, "_live_attempt", fake)
    return attempt


@pytest.fixture
def quiet_pause(monkeypatch):
    """Pauza yo'lidagi Telegram chaqiruvlarini o'chiradi."""

    async def fake_offer_ref(db, order):
        return (123, 456)

    edited: list[tuple[int, int]] = []

    async def fake_notify(offer_ref):
        if offer_ref is not None:
            edited.append(offer_ref)

    monkeypatch.setattr(dispatch_service, "get_pending_offer_message", fake_offer_ref)
    monkeypatch.setattr(dispatch_service, "notify_offer_cancelled", fake_notify)
    return edited


# ────────────────────────────────────────────────────────────
#  1. Narxni qachon o'zgartirish mumkin
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_price_locked_while_offer_is_live(live_attempt):
    """Haydovchida taymer ketayotganda — bloklanadi, qolgan soniya bilan."""
    order = make_order()
    with pytest.raises(dispatch_service.PriceLocked) as exc_info:
        await dispatch_service.ensure_price_editable(FakeSession(), order)

    violation = exc_info.value.violation
    assert violation.code == "DISPATCH_OFFER_ACTIVE"
    # Aniq soniya test ishlagan vaqtga bog'liq — muhimi u berilgan va musbat.
    assert 0 < violation.context["seconds_left"] <= 42


@pytest.mark.asyncio
async def test_price_locked_between_rounds(no_live_attempt):
    """Raundlar orasidagi oraliq ham "qidiruv ketmoqda" hisoblanadi.

    Bu oraliq amalda ~2 soniya (60s taymer vs 62s kechiktirilgan navbat), ya'ni
    unga tayanib narx o'zgartirish poyga bo'lardi: sender tugmani bosguncha keyingi
    haydovchiga taklif allaqachon ketgan bo'ladi.
    """
    order = make_order()
    with pytest.raises(dispatch_service.PriceLocked) as exc_info:
        await dispatch_service.ensure_price_editable(FakeSession(), order)
    assert exc_info.value.violation.code == "DISPATCH_IN_PROGRESS"


@pytest.mark.asyncio
async def test_price_editable_when_paused(no_live_attempt):
    order = make_order(dispatch_paused_at=datetime.now(timezone.utc))
    await dispatch_service.ensure_price_editable(FakeSession(), order)


@pytest.mark.asyncio
async def test_price_editable_when_bump_requested(no_live_attempt):
    """Nomzodlar tugagach tizim o'zi to'xtaydi — narx oshirish aynan shu uchun."""
    order = make_order(price_bump_requested_at=datetime.now(timezone.utc))
    await dispatch_service.ensure_price_editable(FakeSession(), order)


@pytest.mark.asyncio
async def test_price_editable_before_search_starts(no_live_attempt):
    """Rejalashtirilgan yuk: qidiruv hali umuman boshlanmagan."""
    order = make_order(dispatch_round=0, last_dispatch_enqueued_at=None)
    await dispatch_service.ensure_price_editable(FakeSession(), order)


# ────────────────────────────────────────────────────────────
#  2. To'xtatish
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pause_sets_timestamp_and_closes_offer(quiet_pause):
    db = FakeSession()
    order = make_order()

    await dispatch_service.pause_dispatch(db, order)

    assert order.dispatch_paused_at is not None
    # Ochiq urinishlarni yopadigan UPDATE yuborilgan.
    assert len(db.statements) == 1
    # Haydovchining bot kartasi "bekor qilindi" ga o'zgartirilgan.
    assert quiet_pause == [(123, 456)]


@pytest.mark.asyncio
async def test_pause_keeps_dispatch_round(quiet_pause):
    """`dispatch_round` kamaytirilmaydi.

    Aks holda to'xtatish/davom ettirish siklini takrorlab `MAX_ROUNDS` chegarasidan
    cheksiz aylanib o'tish mumkin bo'lardi.
    """
    order = make_order(dispatch_round=3)
    await dispatch_service.pause_dispatch(FakeSession(), order)
    assert order.dispatch_round == 3


@pytest.mark.asyncio
async def test_pause_rejected_when_driver_assigned(quiet_pause):
    order = make_order(driver_id=5)
    with pytest.raises(dispatch_service.DispatchError):
        await dispatch_service.pause_dispatch(FakeSession(), order)


@pytest.mark.asyncio
async def test_pause_rejected_when_already_paused(quiet_pause):
    order = make_order(dispatch_paused_at=datetime.now(timezone.utc))
    with pytest.raises(dispatch_service.DispatchError):
        await dispatch_service.pause_dispatch(FakeSession(), order)


# ────────────────────────────────────────────────────────────
#  3. Davom ettirish
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resume_clears_pause_and_enqueues(monkeypatch):
    published: list[tuple[int, str]] = []

    async def fake_publish(order_id, reason, **kwargs):
        published.append((order_id, reason))

    monkeypatch.setattr(dispatch_service.queue, "publish_dispatch_job", fake_publish)

    order = make_order(dispatch_paused_at=datetime.now(timezone.utc))
    await dispatch_service.resume_dispatch(FakeSession(), order)

    assert order.dispatch_paused_at is None
    assert published == [(1, "resumed")]


@pytest.mark.asyncio
async def test_resume_rejected_when_not_paused():
    with pytest.raises(dispatch_service.DispatchError):
        await dispatch_service.resume_dispatch(FakeSession(), make_order())


# ────────────────────────────────────────────────────────────
#  4. To'xtatilgan buyurtma qayta navbatga tushmasligi
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_paused_order_is_never_enqueued(monkeypatch):
    """`_dispatch_next` — navbatga qo'yishning YAGONA yo'li.

    Shu sababli rad etish, vaqt tugashi va sweep yo'llarining hammasi shu bitta
    tekshiruv bilan yopiladi.
    """
    published: list[tuple[int, str]] = []

    async def fake_publish(order_id, reason, **kwargs):
        published.append((order_id, reason))

    monkeypatch.setattr(dispatch_service.queue, "publish_dispatch_job", fake_publish)

    order = make_order(dispatch_paused_at=datetime.now(timezone.utc))
    for reason in ("rejected", "expired", "requeue", "scheduled_start"):
        await dispatch_service._dispatch_next(FakeSession(), order, reason=reason)

    assert published == []
    # Navbatga tushmagani uchun "oxirgi navbatga qo'yilgan payt" ham yangilanmaydi.
    assert order.last_dispatch_enqueued_at is not None  # eski qiymat o'zgarmagan


@pytest.mark.asyncio
async def test_paused_order_round_is_noop(monkeypatch):
    """Allaqachon navbatdagi kechiktirilgan xabar kelsa ham hech narsa yubormaydi."""
    called = False

    async def fake_candidate(db, order, exclude):
        nonlocal called
        called = True
        return None

    monkeypatch.setattr(dispatch_service, "_find_next_candidate", fake_candidate)

    order = make_order(dispatch_paused_at=datetime.now(timezone.utc))
    await dispatch_service._run_dispatch_round(FakeSession(), order)

    assert called is False
