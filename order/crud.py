from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional, Sequence

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from order.models import Order, OrderRoutePostGIS, OrderStatus, OrderWaypoint
from order.schemas import OrderCreate, OrderUpdate, OrderWaypointCreate
from services import billing, osrm_client, yandex_geocoder

logger = logging.getLogger(__name__)


async def _resolve_waypoint_location(wp: OrderWaypointCreate) -> tuple[Optional[str], float, float]:
    """Waypoint uchun (address, latitude, longitude) — yetishmagan tomonini to'ldiradi.

    - Koordinata berilgan bo'lsa (masalan sender Telegram orqali o'z joylashuvini yuborgan) —
      koordinata ustuvor, manzil matni bo'lmasa reverse-geocoding bilan topiladi.
    - Faqat manzil matni berilgan bo'lsa — Yandex Geocoder orqali qidirilib, eng mos
      (birinchi) natijaning koordinatasi olinadi.
    """
    if wp.latitude is not None and wp.longitude is not None:
        lat, lon = float(wp.latitude), float(wp.longitude)
        address = wp.address
        if not address:
            address = await yandex_geocoder.reverse_geocode(lat, lon)
        return address, lat, lon

    candidates = await yandex_geocoder.search_address(wp.address or "")
    if not candidates:
        raise ValueError(f"Manzil topilmadi: '{wp.address}'")
    best = candidates[0]
    return best.address, best.latitude, best.longitude


async def create_order(db: AsyncSession, data: OrderCreate, *, customer_id: int) -> Order:
    resolved: list[tuple[Optional[str], float, float]] = [
        await _resolve_waypoint_location(wp) for wp in data.waypoints
    ]

    order = Order(
        customer_id=customer_id,
        cargo_name=data.cargo_name,
        weight=data.weight,
        volume=data.volume,
        pickup_at=data.pickup_at,
        required_truck_type_id=data.required_truck_type_id,
        price=data.price,
        currency=data.currency,
        waypoints=[
            OrderWaypoint(
                sequence=wp.sequence,
                type=wp.type,
                address=address,
                latitude=Decimal(str(lat)),
                longitude=Decimal(str(lon)),
                contact_name=wp.contact_name,
                contact_phone=wp.contact_phone,
            )
            for wp, (address, lat, lon) in zip(data.waypoints, resolved)
        ],
    )

    try:
        route = await osrm_client.get_route([(lat, lon) for _, lat, lon in resolved])
    except osrm_client.OSRMRouteError as exc:
        logger.warning("Marshrut hisoblanmadi, buyurtma marshrutsiz yaratiladi: %s", exc)
        route = None

    if route:
        order.total_distance_km = Decimal(str(route.distance_km))
        order.route = OrderRoutePostGIS(geom_route=WKTElement(route.geometry_wkt, srid=4326))

    db.add(order)
    await db.commit()
    await db.refresh(order, attribute_names=["waypoints", "route"])
    return order


async def get_order(db: AsyncSession, order_id: int) -> Optional[Order]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints), selectinload(Order.route))
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def list_orders_by_customer(db: AsyncSession, customer_id: int) -> Sequence[Order]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
    )
    return result.scalars().all()


async def list_orders_by_driver(db: AsyncSession, driver_id: int) -> Sequence[Order]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(Order.driver_id == driver_id)
        .order_by(Order.created_at.desc())
    )
    return result.scalars().all()


async def list_available_orders(db: AsyncSession, *, truck_type_id: Optional[int] = None) -> Sequence[Order]:
    """Hali haydovchisi biriktirilmagan, PENDING holatdagi buyurtmalar (haydovchi ilovasi uchun)."""
    query = (
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(Order.status == OrderStatus.PENDING, Order.driver_id.is_(None))
        .order_by(Order.created_at.desc())
    )
    if truck_type_id is not None:
        query = query.where(Order.required_truck_type_id == truck_type_id)
    result = await db.execute(query)
    return result.scalars().all()


async def update_order(db: AsyncSession, order: Order, data: OrderUpdate) -> Order:
    values = data.model_dump(exclude_unset=True)
    if values:
        await db.execute(update(Order).where(Order.id == order.id).values(**values))
        await db.commit()
        await db.refresh(order, attribute_names=[*values.keys(), "updated_at"])
    return order


async def update_order_status(db: AsyncSession, order: Order, new_status: OrderStatus) -> Order:
    was_completed = order.status == OrderStatus.COMPLETED
    order.status = new_status
    await db.commit()
    await db.refresh(order, attribute_names=["status", "updated_at"])

    # Komissiya faqat PENDING/ACCEPTED/IN_PROGRESS -> COMPLETED o'tishida bir marta yechiladi
    # (allaqachon COMPLETED bo'lgan orderni qayta COMPLETED qilish qayta hisoblamaydi).
    if new_status == OrderStatus.COMPLETED and not was_completed:
        try:
            await billing.charge_order_commission(db, order)
        except Exception:
            logger.exception("Order #%s uchun komissiya yechishda xato", order.id)

    return order


async def assign_driver(db: AsyncSession, order: Order, driver_id: int) -> Order:
    order.driver_id = driver_id
    order.status = OrderStatus.ACCEPTED
    await db.commit()
    await db.refresh(order, attribute_names=["driver_id", "status", "updated_at"])
    return order


async def delete_order(db: AsyncSession, order: Order) -> None:
    await db.delete(order)
    await db.commit()
