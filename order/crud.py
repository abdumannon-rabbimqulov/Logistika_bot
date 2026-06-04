from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from order.models import Order, OrderStatus, OrderWaypoint, OrderOffer
from order.schemas import (
    OrderCreate, OrderUpdate,
    OrderOfferCreate, OrderOfferUpdate
)


def sort_order_waypoints(order: Order) -> Order:
    """Waypoints — sequence (pickup tartibi) bo'yicha."""
    if order.waypoints:
        order.waypoints.sort(key=lambda w: w.sequence)
    return order


async def create_order(db: AsyncSession, data: OrderCreate, *, customer_id: int) -> Order:
    waypoints_data = data.waypoints
    order_dict = data.model_dump()
    del order_dict["waypoints"]

    obj = Order(customer_id=customer_id, **order_dict)
    db.add(obj)
    await db.flush()

    for wp_data in waypoints_data:
        wp = OrderWaypoint(order_id=obj.id, **wp_data.model_dump())
        db.add(wp)

    await db.commit()
    await db.refresh(obj)

    result = await db.execute(
        select(Order).options(selectinload(Order.waypoints)).where(Order.id == obj.id)
    )
    return sort_order_waypoints(result.scalar_one())

async def get_order(db: AsyncSession, pk: int) -> Optional[Order]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints))
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
) -> List[Order]:
    stmt = select(Order).options(selectinload(Order.waypoints))
    if customer_id:
        stmt = stmt.where(Order.customer_id == customer_id)
    if driver_id:
        stmt = stmt.where(Order.driver_id == driver_id)
    if status:
        stmt = stmt.where(Order.status == status)
    if required_truck_type_id is not None:
        stmt = stmt.where(Order.required_truck_type_id == required_truck_type_id)
    if unassigned_only:
        stmt = stmt.where(Order.driver_id.is_(None))

    stmt = stmt.order_by(desc(Order.created_at))
    result = await db.execute(stmt)
    return [sort_order_waypoints(o) for o in result.scalars().all()]


async def get_available_orders_for_driver(
    db: AsyncSession,
    truck_type_id: int,
    *,
    limit: int = 50,
) -> List[Order]:
    """Pending buyurtmalar — haydovchi mashina turiga mos, haydovchisiz."""
    stmt = (
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(
            Order.status == OrderStatus.PENDING,
            Order.driver_id.is_(None),
            Order.required_truck_type_id == truck_type_id,
        )
        .order_by(desc(Order.created_at))
        .limit(min(max(limit, 1), 100))
    )
    result = await db.execute(stmt)
    return [sort_order_waypoints(o) for o in result.scalars().all()]

async def update_order(db: AsyncSession, pk: int, data: OrderUpdate) -> Optional[Order]:
    await db.execute(update(Order).where(Order.id == pk).values(**data.model_dump(exclude_unset=True)))
    await db.commit()
    return await get_order(db, pk)

async def delete_order(db: AsyncSession, pk: int) -> bool:
    await db.execute(delete(Order).where(Order.id == pk))
    await db.commit()
    return True


async def create_order_offer(db: AsyncSession, data: OrderOfferCreate) -> OrderOffer:
    obj = OrderOffer(**data.model_dump())
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
        from datetime import datetime, timezone
        update_data['counter_at'] = datetime.now(timezone.utc)
    
    await db.execute(update(OrderOffer).where(OrderOffer.id == pk).values(**update_data))
    await db.commit()
    return await get_order_offer(db, pk)
