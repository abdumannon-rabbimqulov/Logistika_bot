import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional

from order.models import Order, OrderStatus, OrderWaypoint, OrderOffer
from services.datetime_utils import to_utc_naive, utc_now_naive
from services.notifications import DeletedBy, notify_drivers_order_deleted
from datetime import datetime
logger = logging.getLogger(__name__)


def parse_order_status(raw: Optional[str]) -> Optional[OrderStatus]:
    """Query `status` (pending yoki PENDING) ni OrderStatus enumiga aylantiradi."""
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if not normalized:
        return None
    for member in OrderStatus:
        if member.value.lower() == normalized or member.name.lower() == normalized:
            return member
    return None
from order.schemas import (
    OrderCreate, OrderUpdate,
    OrderOfferCreate, OrderOfferUpdate
)


def sort_order_waypoints(order: Order) -> Order:
    """Waypoints — sequence (pickup tartibi) bo'yicha."""
    if order.waypoints:
        order.waypoints.sort(key=lambda w: w.sequence)
    return order


def _naive_datetime_fields(data: dict) -> dict:
    """TIMESTAMP WITHOUT TIME ZONE ustunlariga faqat naive datetime yuborish."""
    result = {}
    for key, value in data.items():
        if key in ("created_at", "updated_at"):
            continue
        if isinstance(value, datetime):
            result[key] = to_utc_naive(value)
        else:
            result[key] = value
    return result


async def create_order(db: AsyncSession, data: OrderCreate, *, customer_id: int) -> Order:
    waypoints_data = data.waypoints
    order_dict = _naive_datetime_fields(data.model_dump())
    del order_dict["waypoints"]

    obj = Order(customer_id=customer_id, **order_dict)
    db.add(obj)
    await db.flush()

    for wp_data in waypoints_data:
        wp = OrderWaypoint(
            order_id=obj.id,
            **_naive_datetime_fields(wp_data.model_dump()),
        )
        db.add(wp)

    await db.commit()
    await db.refresh(obj)

    result = await db.execute(
        select(Order).options(selectinload(Order.waypoints)).where(Order.id == obj.id)
    )
    return sort_order_waypoints(result.scalar_one())

async def get_order(db: AsyncSession, pk: int) -> Optional[Order]:
    from driver.models import Driver
    result = await db.execute(
        select(Order)
        .options(
            selectinload(Order.waypoints),
            selectinload(Order.customer),
            selectinload(Order.driver).selectinload(Driver.user),
            selectinload(Order.chat)
        )
        .where(Order.id == pk)
    )
    order = result.scalar_one_or_none()
    return sort_order_waypoints(order) if order else None

async def get_all_orders(
    db: AsyncSession,
    customer_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    status: Optional[str] = None,
    *,
    required_truck_type_id: Optional[int] = None,
    unassigned_only: bool = False,
    limit: Optional[int] = None,
) -> List[Order]:
    stmt = select(Order).options(selectinload(Order.waypoints))
    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)
    if driver_id is not None:
        stmt = stmt.where(Order.driver_id == driver_id)
    parsed_status = parse_order_status(status)
    if parsed_status is not None:
        stmt = stmt.where(Order.status == parsed_status)
    if required_truck_type_id is not None:
        stmt = stmt.where(Order.required_truck_type_id == required_truck_type_id)
    if unassigned_only:
        stmt = stmt.where(Order.driver_id.is_(None))

    stmt = stmt.order_by(desc(Order.created_at))
    if limit is not None:
        stmt = stmt.limit(min(max(limit, 1), 500))
    result = await db.execute(stmt)
    return [sort_order_waypoints(o) for o in result.scalars().all()]


async def list_driver_marketplace_orders(
    db: AsyncSession,
    *,
    status: OrderStatus = OrderStatus.PENDING,
    truck_type_id: Optional[int] = None,
    limit: int = 200,
) -> List[Order]:
    """Haydovchi bozori — admin `/system/orders` bilan bir xil Order jadvali.

    Admin panel status filtrsiz hamma buyurtmani ko'radi; haydovchi uchun faqat
    tayinlanmagan (driver_id IS NULL) va berilgan status (odatda pending).
    truck_type_id berilsa — required_truck_type_id filtri (filter_by_truck).
    """
    stmt = (
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(Order.status == status)
        .where(Order.driver_id.is_(None))
    )
    if truck_type_id is not None:
        stmt = stmt.where(Order.required_truck_type_id == truck_type_id)

    stmt = stmt.order_by(desc(Order.created_at)).limit(min(max(limit, 1), 500))
    result = await db.execute(stmt)
    return [sort_order_waypoints(o) for o in result.scalars().all()]


async def get_available_orders_for_driver(
    db: AsyncSession,
    truck_type_id: int,
    *,
    limit: int = 50,
    relax_truck: bool = False,
) -> List[Order]:
    """Pending buyurtmalar — haydovchisiz; relax_truck bo'lsa mashina turi filtri yo'q."""
    conditions = [
        Order.status == OrderStatus.PENDING,
        Order.driver_id.is_(None),
    ]
    if not relax_truck:
        conditions.append(Order.required_truck_type_id == truck_type_id)

    stmt = (
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(*conditions)
        .order_by(desc(Order.created_at))
        .limit(min(max(limit, 1), 100))
    )
    result = await db.execute(stmt)
    return [sort_order_waypoints(o) for o in result.scalars().all()]

async def update_order(db: AsyncSession, pk: int, data: OrderUpdate) -> Optional[Order]:
    await db.execute(update(Order).where(Order.id == pk).values(**data.model_dump(exclude_unset=True)))
    await db.commit()
    return await get_order(db, pk)

async def delete_order(
    db: AsyncSession,
    pk: int,
    *,
    deleted_by: DeletedBy = "admin",
) -> bool:
    """Buyurtmani o'chirish: taklif bergan haydovchilarga xabar, keyin offer → order."""
    order_row = await db.execute(
        select(Order.id, Order.cargo_name).where(Order.id == pk)
    )
    row = order_row.one_or_none()
    if row is None:
        return False

    cargo_name = row.cargo_name

    driver_ids_result = await db.execute(
        select(OrderOffer.driver_id)
        .where(OrderOffer.order_id == pk)
        .distinct()
    )
    driver_ids = [int(d) for d in driver_ids_result.scalars().all()]

    try:
        await notify_drivers_order_deleted(
            db, driver_ids, cargo_name, deleted_by=deleted_by
        )
    except Exception as exc:
        logger.warning(
            "Buyurtma #%s o'chirilganda haydovchilarga xabar yuborilmadi: %s",
            pk,
            exc,
        )

    await db.execute(delete(OrderOffer).where(OrderOffer.order_id == pk))
    await db.execute(delete(Order).where(Order.id == pk))
    await db.commit()
    return True


async def create_order_offer(db: AsyncSession, data: OrderOfferCreate) -> OrderOffer:
    offer_dict = data.model_dump()
    allowed_keys = OrderOffer.__table__.columns.keys()
    safe_offer_data = {k: v for k, v in offer_dict.items() if k in allowed_keys}
    obj = OrderOffer(**safe_offer_data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_order_offer(db: AsyncSession, pk: int) -> Optional[OrderOffer]:
    result = await db.execute(select(OrderOffer).where(OrderOffer.id == pk))
    return result.scalar_one_or_none()

async def get_order_offers(db: AsyncSession, order_id: int) -> List[OrderOffer]:
    result = await db.execute(select(OrderOffer).where(OrderOffer.order_id == order_id))
    return result.scalars().all()

async def update_order_offer(db: AsyncSession, pk: int, data: OrderOfferUpdate) -> Optional[OrderOffer]:
    update_data = data.model_dump(exclude_unset=True)
    if 'counter_price' in update_data:
        update_data['counter_at'] = utc_now_naive()
    
    await db.execute(update(OrderOffer).where(OrderOffer.id == pk).values(**update_data))
    await db.commit()
    return await get_order_offer(db, pk)
