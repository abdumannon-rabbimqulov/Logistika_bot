#!/usr/bin/env python3
"""
Test ma'lumotlarini PostgreSQL bazasiga yozish (async SQLAlchemy + asyncpg).

Joylashuv:  Logistika_bot/scripts/seed_test_data.py

O'rnatish:
    cd Logistika_bot
    source .venv/bin/activate
    pip install -r requirements.txt

Ishga tushirish:
    python scripts/seed_test_data.py

Muhit: .env ichida DB_URL (masalan postgresql+asyncpg://user:pass@127.0.0.1:5432/dbname)

Eslatma: Loyihada mijoz roli `UserRole.SENDER` (customer_id = users.id).
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import configure_mappers

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _require_deps() -> None:
    missing: list[str] = []
    for pkg in ("asyncpg", "bcrypt", "greenlet"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(
            "❌ Yetishmayotgan paketlar: "
            + ", ".join(missing)
            + "\n   pip install -r requirements.txt"
        )
        sys.exit(1)


_require_deps()

import driver.models  # noqa: E402, F401
import order.models  # noqa: E402, F401
import ai.models  # noqa: E402, F401
import users.models  # noqa: E402, F401

configure_mappers()

from config.config import async_session  # noqa: E402
from driver.models import Driver, TruckType  # noqa: E402
from order.models import (  # noqa: E402
    OfferStatus,
    Order,
    OrderOffer,
    OrderStatus,
    OrderTrack,
    OrderWaypoint,
    WaypointStatus,
    WaypointType,
)
from users.models import User, UserRole  # noqa: E402

# --- Konstantalar ---
SEED_PREFIX = "[SEED]"
SENDER_USER_ID = 880_001_000
SENDER_EMAIL = "seed-toshkent-logistika@test.local"
SENDER_PHONE = "+998900001000"
TARGET_DRIVER_ID = 1  # Tursunoy

WP_TYPES = {
    "pickup": WaypointType.PICKUP,
    "delivery": WaypointType.DELIVERY,
    "transit": WaypointType.TRANSIT,
}


def _utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_password(plain: str) -> str:
    from users.auth import hash_password

    return hash_password(plain)


def _order_specs() -> list[dict]:
    """
    sequence, waypoint_type, address, note (amal).
    """
    return [
        {
            "cargo_name": f"{SEED_PREFIX} Meva-cheva",
            "weight": Decimal("11.50"),
            "volume": Decimal("32.00"),
            "price": Decimal("3200000.00"),
            "total_distance_km": Decimal("480.00"),
            "waypoints": [
                (1, "pickup", "Toshkent, Chilonzor logistika hududi", "Yuklash"),
                (2, "delivery", "Samarqand, Registon yo'nalishi", "Tushirish"),
            ],
        },
        {
            "cargo_name": f"{SEED_PREFIX} Qurilish mollari",
            "weight": Decimal("18.00"),
            "volume": Decimal("45.00"),
            "price": Decimal("4500000.00"),
            "total_distance_km": Decimal("380.00"),
            "waypoints": [
                (1, "pickup", "Toshkent, Sergeli sanoat zonasi", "Yuklash"),
                (2, "delivery", "Guliston, markaziy ombor", "Yuk tushirish"),
                (3, "delivery", "Jizzax, sanoat hududi", "Yakuniy tushirish"),
            ],
        },
        {
            "cargo_name": f"{SEED_PREFIX} Maishiy texnika",
            "weight": Decimal("9.20"),
            "volume": Decimal("55.00"),
            "price": Decimal("6100000.00"),
            "total_distance_km": Decimal("720.00"),
            "waypoints": [
                (1, "pickup", "Farg'ona, Qo'qon yo'li", "Yuklash"),
                (2, "transit", "Qo'qon, bozor yonidagi ombor", "Qo'shimcha yuklash"),
                (3, "delivery", "Toshkent, Olmazor logistika markazi", "Yuk tushirish"),
                (4, "delivery", "Sirdaryo, Yangiyer shahri", "Yakuniy tushirish"),
            ],
        },
        {
            "cargo_name": f"{SEED_PREFIX} Poliz ekinlari",
            "weight": Decimal("14.00"),
            "volume": Decimal("28.00"),
            "price": Decimal("2800000.00"),
            "total_distance_km": Decimal("195.00"),
            "waypoints": [
                (1, "pickup", "Buxoro, Kogon yo'nalishi", "Yuklash"),
                (2, "delivery", "Navoiy, kon-metallurgiya zonasi", "Tushirish"),
            ],
        },
        {
            "cargo_name": f"{SEED_PREFIX} Kiyim-kechak",
            "weight": Decimal("6.80"),
            "volume": Decimal("40.00"),
            "price": Decimal("5400000.00"),
            "total_distance_km": Decimal("650.00"),
            "waypoints": [
                (1, "pickup", "Xorazm, Urganch shahar", "Yuklash"),
                (2, "delivery", "Buxoro, tarixiy markaz yonida", "Yuk tushirish"),
                (3, "delivery", "Samarqand, Temur ko'chasi", "Yakuniy tushirish"),
            ],
        },
    ]


async def cleanup_seed_orders(session) -> None:
    """[SEED] buyurtmalar va ularga bog'liq offer/track/waypointlarni o'chirish."""
    seed_ids = (
        await session.execute(
            select(Order.id).where(Order.cargo_name.like(f"{SEED_PREFIX}%"))
        )
    ).scalars().all()

    if not seed_ids:
        print("  (Tozalash: oldingi [SEED] buyurtmalar topilmadi)")
        return

    await session.execute(delete(OrderOffer).where(OrderOffer.order_id.in_(seed_ids)))
    await session.execute(delete(OrderTrack).where(OrderTrack.order_id.in_(seed_ids)))
    await session.execute(delete(OrderWaypoint).where(OrderWaypoint.order_id.in_(seed_ids)))
    await session.execute(delete(Order).where(Order.id.in_(seed_ids)))
    await session.flush()
    print(f"  + Tozalandi: {len(seed_ids)} ta [SEED] buyurtma (+ offer/waypoint/track)")


async def ensure_sender(session) -> User:
    user = (
        await session.execute(select(User).where(User.id == SENDER_USER_ID))
    ).scalar_one_or_none()
    if user:
        user.full_name = "Toshkent Logistika MChJ"
        user.role = UserRole.SENDER
        user.email = SENDER_EMAIL
        user.phone_number = SENDER_PHONE
        user.is_active = True
        print(f"  = Sender yangilandi: id={user.id}")
        return user

    user = User(
        id=SENDER_USER_ID,
        full_name="Toshkent Logistika MChJ",
        email=SENDER_EMAIL,
        phone_number=SENDER_PHONE,
        password=_hash_password("SeedSender123!"),
        role=UserRole.SENDER,
        is_active=True,
        language="uz",
        balance=Decimal("5000000.00"),
    )
    session.add(user)
    await session.flush()
    print(f"  + Sender yaratildi: id={user.id} ({user.full_name})")
    return user


async def get_truck_type_id(session) -> int:
    driver = await session.get(Driver, TARGET_DRIVER_ID)
    if driver:
        return driver.truck_type_id

    tt = (
        await session.execute(
            select(TruckType).where(TruckType.is_active == True).limit(1)  # noqa: E712
        )
    ).scalar_one_or_none()
    if tt:
        return tt.id

    tt = TruckType(
        name=f"{SEED_PREFIX} Yuk mashinasi",
        max_weight=Decimal("25.00"),
        max_volume=Decimal("90.00"),
        is_active=True,
    )
    session.add(tt)
    await session.flush()
    return tt.id


async def require_driver(session, truck_type_id: int) -> Driver:
    driver = await session.get(Driver, TARGET_DRIVER_ID)
    if not driver:
        raise RuntimeError(
            f"Haydovchi id={TARGET_DRIVER_ID} (Tursunoy) bazada yo'q. "
            "Avval haydovchi profilini yarating."
        )

    # Model ustunlari: total_km, on_time_percent, cancel_count, total_trips, ...
    driver.truck_type_id = truck_type_id
    driver.is_available = True
    driver.is_blocked = False
    driver.docs_verified = True
    if driver.total_km is None:
        driver.total_km = 0
    if driver.cancel_count is None:
        driver.cancel_count = 0
    if driver.on_time_percent is None:
        driver.on_time_percent = Decimal("100.00")
    if driver.rating is None:
        driver.rating = Decimal("5.00")

    print(
        f"  = Haydovchi: id={driver.id}, truck_type_id={driver.truck_type_id}, "
        f"total_km={driver.total_km}, on_time={driver.on_time_percent}%, "
        f"cancel_count={driver.cancel_count}"
    )
    return driver


async def create_orders(
    session,
    *,
    customer_id: int,
    truck_type_id: int,
) -> list[Order]:
    now = _utc_now_naive()
    orders: list[Order] = []

    for spec in _order_specs():
        order = Order(
            customer_id=customer_id,
            driver_id=None,
            cargo_name=spec["cargo_name"],
            weight=spec["weight"],
            volume=spec["volume"],
            required_truck_type_id=truck_type_id,
            price=spec["price"],
            currency="UZS",
            total_distance_km=spec["total_distance_km"],
            status=OrderStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        session.add(order)
        await session.flush()

        for seq, wp_key, address, note in spec["waypoints"]:
            session.add(
                OrderWaypoint(
                    order_id=order.id,
                    sequence=seq,
                    waypoint_type=WP_TYPES[wp_key],
                    address=address,
                    note=note,
                    status=WaypointStatus.PENDING,
                    created_at=now,
                    updated_at=now,
                )
            )

        await session.flush()
        orders.append(order)
        print(
            f"  + Order id={order.id}: {spec['cargo_name']} "
            f"({len(spec['waypoints'])} waypoint)"
        )

    return orders


async def create_offers(
    session,
    *,
    orders: list[Order],
    driver_id: int,
) -> int:
    now = _utc_now_naive()
    count = 0

    for order in orders:
        offer = OrderOffer(
            order_id=order.id,
            driver_id=driver_id,
            offered_price=order.price,
            currency="UZS",
            status=OfferStatus.PENDING,
            comment=f"{SEED_PREFIX} Tursunoy taklifi",
            is_seen=False,
            created_at=now,
            updated_at=now,
        )
        session.add(offer)
        count += 1

    await session.flush()
    return count


async def run_seed() -> None:
    print("=== Logistika seed_test_data ===\n")

    async with async_session() as session:
        try:
            print("1) [SEED] buyurtmalarni tozalash...")
            await cleanup_seed_orders(session)

            print("\n2) Sender (mijoz)...")
            sender = await ensure_sender(session)

            print("\n3) Haydovchi va mashina turi...")
            truck_type_id = await get_truck_type_id(session)
            driver = await require_driver(session, truck_type_id)

            print("\n4) 5 ta pending buyurtma + waypoints...")
            orders = await create_orders(
                session,
                customer_id=sender.id,
                truck_type_id=truck_type_id,
            )

            print("\n5) 5 ta pending OrderOffer (driver_id=1)...")
            offer_count = await create_offers(
                session,
                orders=orders,
                driver_id=driver.id,
            )
            for o in orders:
                print(f"     Offer: order_id={o.id} -> driver_id={driver.id}")

            await session.commit()

            print("\n✅ Muvaffaqiyatli yakunlandi.")
            print(f"   Sender id={sender.id}")
            print(f"   Orders: {len(orders)} (pending)")
            print(f"   Offers: {offer_count} (pending, driver_id={TARGET_DRIVER_ID})")
            print(
                "\nTekshirish:"
                f"\n  GET /api/orders/?status=PENDING&filter_by_truck=false"
                f"\n  GET /api/orders/?status=PENDING&filter_by_truck=true "
                f"(driver truck_type_id={driver.truck_type_id})"
            )
            print(
                "  Agar bo'sh bo'lsa: .env da RELAX_DRIVER_ORDER_FILTERS=1 "
                "yoki seedni qayta ishga tushiring."
            )
        except Exception as exc:
            await session.rollback()
            low = str(exc).lower()
            if "nodename" in low or "connect" in low or "gaierror" in low:
                print(
                    "\n❌ Bazaga ulanib bo'lmadi. PostgreSQL va .env DB_URL ni tekshiring."
                )
            print(f"❌ {type(exc).__name__}: {exc}")
            raise


def main() -> None:
    asyncio.run(run_seed())


if __name__ == "__main__":
    main()
