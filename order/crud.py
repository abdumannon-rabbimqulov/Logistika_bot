from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from order.models import Order, OrderWaypoint, OrderOffer
from order.schemas import (
    OrderCreate, OrderUpdate,
    OrderOfferCreate, OrderOfferUpdate
)

# --- Order CRUD ---

async def create_order(db: AsyncSession, data: OrderCreate) -> Order:
    waypoints_data = data.waypoints
    order_dict = data.model_dump()
    del order_dict['waypoints']
    
    obj = Order(**order_dict)
    db.add(obj)
    await db.flush()  # To get obj.id

    for wp_data in waypoints_data:
        wp = OrderWaypoint(order_id=obj.id, **wp_data.model_dump())
        db.add(wp)
    
    await db.commit()
    await db.refresh(obj)
    # Load waypoints for response
    result = await db.execute(
        select(Order).options(selectinload(Order.waypoints)).where(Order.id == obj.id)
    )
    return result.scalar_one()

async def get_order(db: AsyncSession, pk: int) -> Optional[Order]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(Order.id == pk)
    )
    return result.scalar_one_or_none()

async def get_all_orders(
    db: AsyncSession, 
    customer_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    status: Optional[str] = None
) -> List[Order]:
    stmt = select(Order).options(selectinload(Order.waypoints))
    if customer_id:
        stmt = stmt.where(Order.customer_id == customer_id)
    if driver_id:
        stmt = stmt.where(Order.driver_id == driver_id)
    if status:
        stmt = stmt.where(Order.status == status)
    
    result = await db.execute(stmt)
    return result.scalars().all()

async def update_order(db: AsyncSession, pk: int, data: OrderUpdate) -> Optional[Order]:
    await db.execute(update(Order).where(Order.id == pk).values(**data.model_dump(exclude_unset=True)))
    await db.commit()
    return await get_order(db, pk)

async def delete_order(db: AsyncSession, pk: int) -> bool:
    await db.execute(delete(Order).where(Order.id == pk))
    await db.commit()
    return True

# --- OrderOffer CRUD ---

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
