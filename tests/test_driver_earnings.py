"""Haydovchi daromadlari: buyurtma va undan olingan komissiyani bog'lash.

"Daromad" ekrani ilgari faqat buyurtmalar ro'yxatidan qurilardi va platforma qancha
komissiya ushlab qolganini UMUMAN ko'rsatmasdi. Endi `services/billing.py`
`list_driver_earnings` buyurtmalarni `balance_transactions` jadvalidagi
`ORDER_COMMISSION` yozuvlari bilan bitta so'rovda birlashtiradi.

Bazasiz: so'rov ushlab qolinadi va SQL darajasida tekshiriladi, natijani shakllantirish
mantiqi esa soxta qatorlar bilan sinaladi.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from order.models import Order, OrderStatus, OrderWaypoint, WaypointStatus, WaypointType
from services import billing


def make_waypoint(wp_id: int, sequence: int, wp_type: WaypointType, address: str) -> OrderWaypoint:
    wp = OrderWaypoint()
    wp.id = wp_id
    wp.sequence = sequence
    wp.type = wp_type
    wp.status = WaypointStatus.COMPLETED
    wp.address = address
    return wp


def make_order(order_id: int = 1, price: str = "1650000.00") -> Order:
    order = Order()
    order.id = order_id
    order.cargo_name = "Olma"
    order.price = Decimal(price)
    order.currency = "UZS"
    order.status = OrderStatus.COMPLETED
    order.completed_at = datetime(2026, 7, 30, 14, 30, tzinfo=timezone.utc)
    order.waypoints = [
        make_waypoint(1, 1, WaypointType.PICKUP, "Toshkent, Chilonzor 5"),
        make_waypoint(2, 2, WaypointType.DELIVERY, "Samarqand, Registon 1"),
    ]
    return order


class CapturingSession:
    """`list_driver_earnings` ga soxta natija qaytaradi va SELECT ni saqlab qoladi."""

    def __init__(self, rows=None):
        self.rows = rows or []
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        rows = self.rows

        class _Result:
            @staticmethod
            def all():
                return rows

        return _Result()

    def sql(self) -> str:
        return str(self.statement.compile(compile_kwargs={"literal_binds": True}))


async def earnings(rows) -> list[dict]:
    return await billing.list_driver_earnings(CapturingSession(rows), 42)


# ────────────────────────────────────────────────────────────
#  1. Komissiya hisobi
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_commission_is_reported_as_positive_amount():
    """Bazada komissiya MANFIY saqlanadi (balansdan yechiladi), UI ga musbat chiqadi."""
    order = make_order(price="1650000.00")

    [item] = await earnings([(order, Decimal("-165000.00"))])

    assert item["gross_amount"] == Decimal("1650000.00")
    assert item["commission_amount"] == Decimal("165000.00")
    assert item["net_amount"] == Decimal("1485000.00")


@pytest.mark.asyncio
async def test_net_equals_gross_minus_commission():
    order = make_order(price="500000.00")

    [item] = await earnings([(order, Decimal("-50000.00"))])

    assert item["net_amount"] == item["gross_amount"] - item["commission_amount"]


@pytest.mark.asyncio
async def test_order_without_commission_still_listed():
    """LEFT JOIN: komissiya yozuvi yo'q buyurtma ham ro'yxatdan tushib qolmaydi.

    Masalan tizimda komissiya joriy qilinishidan oldin yakunlangan yuklar.
    """
    order = make_order(price="300000.00")

    [item] = await earnings([(order, None)])

    assert item["commission_amount"] == Decimal("0.00")
    assert item["net_amount"] == Decimal("300000.00")


@pytest.mark.asyncio
async def test_multiple_commission_rows_are_summed():
    """Bir buyurtma bo'yicha bir nechta yozuv bo'lsa (qo'lda tuzatish) — yig'indi olinadi.

    So'rovda `SUM` ishlatilgani uchun bu yerga allaqachon jamlangan qiymat keladi.
    """
    order = make_order(price="1000000.00")

    [item] = await earnings([(order, Decimal("-120000.00"))])

    assert item["commission_amount"] == Decimal("120000.00")


# ────────────────────────────────────────────────────────────
#  2. Buyurtma ma'lumotlari
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_order_identity_and_route_included():
    """Haydovchi daromad qaysi buyurtmadan ekanini ko'rishi kerak."""
    order = make_order(order_id=77)

    [item] = await earnings([(order, Decimal("-10000.00"))])

    assert item["order_id"] == 77
    assert item["cargo_name"] == "Olma"
    assert item["origin_address"] == "Toshkent, Chilonzor 5"
    assert item["destination_address"] == "Samarqand, Registon 1"
    assert item["currency"] == "UZS"
    assert item["completed_at"] == datetime(2026, 7, 30, 14, 30, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_order_without_waypoints_has_null_addresses():
    order = make_order()
    order.waypoints = []

    [item] = await earnings([(order, None)])

    assert item["origin_address"] is None
    assert item["destination_address"] is None


# ────────────────────────────────────────────────────────────
#  3. So'rovning o'zi (SQL)
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_query_joins_commission_and_filters_by_driver():
    db = CapturingSession()
    await billing.list_driver_earnings(db, 42, skip=0, limit=20)
    sql = db.sql()

    # Faqat shu haydovchining YAKUNLANGAN buyurtmalari
    assert "drivers.user_id = 42" in sql
    assert "orders.status = 'COMPLETED'" in sql
    # Komissiya balance_transactions dan, faqat ORDER_COMMISSION turi
    assert "balance_transactions" in sql
    assert "'ORDER_COMMISSION'" in sql
    # Komissiyasiz buyurtma tushib qolmasligi uchun LEFT JOIN
    assert "LEFT OUTER JOIN" in sql
    # Eng yangi yakunlangani birinchi
    assert "ORDER BY orders.completed_at DESC" in sql


@pytest.mark.asyncio
async def test_limit_is_capped():
    """Juda katta `limit` bilan butun tarixni tortib olib bo'lmaydi."""
    db = CapturingSession()
    await billing.list_driver_earnings(db, 42, limit=10_000)

    assert "LIMIT 100" in db.sql()
