"""Rejalashtirilgan buyurtmalar: qidiruv qachon boshlanishi va sana taqqoslash.

Ikki muammo qulflanadi:

1. Ilgari qidiruv buyurtma yaratilishi bilanoq boshlanardi — 2 kundan keyingi yuk uchun
   ham. Haydovchi taklifni qabul qilib, ikki kunga band bo'lib qolardi. Endi qidiruv
   yuklashdan `DISPATCH_START_LEAD_SEC` oldin boshlanadi.
2. Haydovchining "qachondan yuk olaman" sanasi UTC bo'yicha taqqoslanardi. Toshkent
   UTC+5 bo'lgani uchun tundagi yuklarda sana bir kunga surilib ketardi.

Bazasiz: `Order` obyektlari xotirada quriladi, navbat monkeypatch qilinadi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from order.models import Order, OrderStatus
from services import dispatch as dispatch_service

LEAD = dispatch_service.DISPATCH_START_LEAD_SEC


class FakeSession:
    """`_dispatch_next` ishlatadigan sessiya usullarining o'rnini bosuvchi."""

    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj, attribute_names=None) -> None:
        return None


def make_order(*, pickup_in: timedelta, **overrides) -> Order:
    order = Order()
    order.id = 1
    order.status = OrderStatus.PENDING
    order.driver_id = None
    order.dispatch_round = 0
    order.last_dispatch_enqueued_at = None
    order.price_bump_requested_at = None
    order.pickup_at = datetime.now(timezone.utc) + pickup_in
    for key, value in overrides.items():
        setattr(order, key, value)
    return order


@pytest.fixture
def published(monkeypatch):
    """Navbatga qo'yilgan vazifalarni yozib boradi."""
    calls: list[tuple[int, str]] = []

    async def fake_publish(order_id, reason, **kwargs):
        calls.append((order_id, reason))

    monkeypatch.setattr(dispatch_service.queue, "publish_dispatch_job", fake_publish)
    return calls


# ────────────────────────────────────────────────────────────
#  1. Qidiruv qachon boshlanadi
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("label", "pickup_in", "should_start"),
    [
        ("yuklash o'tib ketgan", timedelta(minutes=-5), True),
        ("1 soatdan keyin", timedelta(hours=1), True),
        ("oynaga sal kirgan", timedelta(seconds=LEAD - 600), True),
        ("aynan chegarada", timedelta(seconds=LEAD - 1), True),
        ("oynadan sal tashqarida", timedelta(seconds=LEAD + 600), False),
        ("2 kundan keyin", timedelta(days=2), False),
        ("30 kundan keyin", timedelta(days=30), False),
    ],
)
@pytest.mark.asyncio
async def test_start_dispatch_respects_lead_window(published, label, pickup_in, should_start):
    order = make_order(pickup_in=pickup_in)

    await dispatch_service.start_dispatch(FakeSession(), order)

    assert bool(published) is should_start, label


@pytest.mark.asyncio
async def test_scheduled_order_stays_untouched(published):
    """Kechiktirilgan buyurtma PENDING va "hali boshlanmagan" holatida qoladi."""
    order = make_order(pickup_in=timedelta(days=2))

    await dispatch_service.start_dispatch(FakeSession(), order)

    assert published == []
    assert order.status == OrderStatus.PENDING
    # Bu ustun NULL qolishi shart — `enqueue_due_orders` aynan shunga qarab topadi.
    assert order.last_dispatch_enqueued_at is None


def test_dispatch_starts_at_is_pickup_minus_lead():
    order = make_order(pickup_in=timedelta(days=2))
    expected = order.pickup_at - timedelta(seconds=LEAD)
    assert dispatch_service.dispatch_starts_at(order) == expected


def test_is_dispatch_due_boundary():
    order = make_order(pickup_in=timedelta(seconds=LEAD))
    now = datetime.now(timezone.utc)

    assert dispatch_service.is_dispatch_due(order, now=now + timedelta(seconds=5))
    assert not dispatch_service.is_dispatch_due(order, now=now - timedelta(seconds=5))


def test_naive_pickup_treated_as_utc():
    """Mintaqasiz `pickup_at` (eski yozuvlar) hisobni buzmasligi kerak."""
    order = make_order(pickup_in=timedelta(days=2))
    order.pickup_at = order.pickup_at.replace(tzinfo=None)

    assert dispatch_service.dispatch_starts_at(order).tzinfo is not None
    assert not dispatch_service.is_dispatch_due(order)


# ────────────────────────────────────────────────────────────
#  2. Sana taqqoslash mahalliy mintaqada
# ────────────────────────────────────────────────────────────

def test_local_pickup_date_uses_app_timezone():
    """2-avgust 03:00 Toshkent = 1-avgust 22:00 UTC — sana 08-02 bo'lishi kerak.

    UTC sana ishlatilganda 2-avgustdan liniyaga chiqqan haydovchi aynan shu
    2-avgustdagi yukni olmay qolardi.
    """
    tashkent = ZoneInfo("Asia/Tashkent")
    order = make_order(pickup_in=timedelta(days=1))
    order.pickup_at = datetime(2026, 8, 2, 3, 0, tzinfo=tashkent)

    assert order.pickup_at.astimezone(timezone.utc).date().isoformat() == "2026-08-01"
    assert dispatch_service.local_pickup_date(order).isoformat() == "2026-08-02"


def test_local_pickup_date_midday_unchanged():
    """Kunduzgi yuklarda UTC va mahalliy sana bir xil — regressiya yo'qligi uchun."""
    tashkent = ZoneInfo("Asia/Tashkent")
    order = make_order(pickup_in=timedelta(days=1))
    order.pickup_at = datetime(2026, 8, 2, 14, 0, tzinfo=tashkent)

    assert dispatch_service.local_pickup_date(order).isoformat() == "2026-08-02"


def test_local_pickup_date_accepts_naive():
    order = make_order(pickup_in=timedelta(days=1))
    order.pickup_at = datetime(2026, 8, 2, 12, 0)  # mintaqasiz → UTC deb olinadi
    # UTC 12:00 → Toshkent 17:00, sana o'zgarmaydi
    assert dispatch_service.local_pickup_date(order).isoformat() == "2026-08-02"


# ────────────────────────────────────────────────────────────
#  3. Sweep so'rovlari (SQL darajasida)
# ────────────────────────────────────────────────────────────

class CapturingSession(FakeSession):
    """`execute` ga kelgan SELECT larni yozib oladi va bo'sh natija qaytaradi."""

    def __init__(self) -> None:
        super().__init__()
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)

        class _Result:
            @staticmethod
            def scalars():
                class _Scalars:
                    @staticmethod
                    def all():
                        return []

                return _Scalars()

        return _Result()

    def sql(self) -> str:
        return str(self.statements[-1].compile(compile_kwargs={"literal_binds": False}))


@pytest.mark.asyncio
async def test_enqueue_due_orders_filters_on_pickup_window():
    db = CapturingSession()
    assert await dispatch_service.enqueue_due_orders(db) == 0

    sql = db.sql()
    # Faqat hali boshlanmagan va vaqti kelgan buyurtmalar olinadi
    assert "orders.pickup_at <=" in sql
    assert "orders.last_dispatch_enqueued_at IS NULL" in sql
    assert "orders.dispatch_round =" in sql


@pytest.mark.asyncio
async def test_requeue_stuck_orders_excludes_future_orders():
    """Regressiya: kelajakdagi buyurtma "qidiruvsiz qolgan" deb hisoblanmasligi kerak.

    Bu shart bo'lmasa sweep har 20 soniyada rejalashtirilgan buyurtmani qidiruvga
    tashlab, butun kechiktirishni bekor qilib qo'yardi.
    """
    db = CapturingSession()
    assert await dispatch_service.requeue_stuck_orders(db) == 0

    assert "orders.pickup_at <=" in db.sql()
