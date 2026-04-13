from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import OfferStatus, Order, OrderOffer, OrderStatus
from schemas import (
    OrderCreate, OrderOfferCreate, OrderOfferUpdate, OrderUpdate,
)


# ──────────────────────────────────────────────
#  ORDER CRUD
# ──────────────────────────────────────────────

async def create_order(
    db: AsyncSession,
    customer_id: int,
    data: OrderCreate,
) -> Order:
    order = Order(**data.model_dump(), customer_id=customer_id)
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_order(
    db: AsyncSession,
    order_id: int,
    with_offers: bool = False,
) -> Optional[Order]:
    stmt = select(Order).where(Order.id == order_id)
    if with_offers:
        stmt = stmt.options(selectinload(Order.offers))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_orders(
    db: AsyncSession,
    *,
    customer_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    status: Optional[OrderStatus] = None,
    from_city: Optional[str] = None,
    to_city: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> Sequence[Order]:
    stmt = select(Order)

    if customer_id is not None:
        stmt = stmt.where(Order.customer_id == customer_id)
    if driver_id is not None:
        stmt = stmt.where(Order.driver_id == driver_id)
    if status is not None:
        stmt = stmt.where(Order.status == status)
    if from_city is not None:
        stmt = stmt.where(Order.from_city.ilike(f"%{from_city}%"))
    if to_city is not None:
        stmt = stmt.where(Order.to_city.ilike(f"%{to_city}%"))

    stmt = stmt.offset(skip).limit(limit).order_by(Order.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_order(
    db: AsyncSession,
    order: Order,
    data: OrderUpdate,
) -> Order:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(order, field, value)
    await db.commit()
    await db.refresh(order)
    return order


async def update_order_status(
    db: AsyncSession,
    order: Order,
    status: OrderStatus,
) -> Order:
    order.status = status
    await db.commit()
    await db.refresh(order)
    return order


async def assign_driver_to_order(
    db: AsyncSession,
    order: Order,
    driver_id: int,
) -> Order:
    order.driver_id = driver_id
    order.status = OrderStatus.ACCEPTED
    await db.commit()
    await db.refresh(order)
    return order


async def delete_order(db: AsyncSession, order: Order) -> None:
    await db.delete(order)
    await db.commit()


# ──────────────────────────────────────────────
#  ORDER OFFER CRUD
# ──────────────────────────────────────────────

async def create_offer(
    db: AsyncSession,
    order_id: int,
    driver_id: int,
    data: OrderOfferCreate,
) -> OrderOffer:
    offer = OrderOffer(
        **data.model_dump(),
        order_id=order_id,
        driver_id=driver_id,
    )
    db.add(offer)
    await db.commit()
    await db.refresh(offer)
    return offer


async def get_offer(
    db: AsyncSession,
    offer_id: int,
) -> Optional[OrderOffer]:
    result = await db.execute(
        select(OrderOffer).where(OrderOffer.id == offer_id)
    )
    return result.scalar_one_or_none()


async def get_offers_for_order(
    db: AsyncSession,
    order_id: int,
    status: Optional[OfferStatus] = None,
) -> Sequence[OrderOffer]:
    stmt = select(OrderOffer).where(OrderOffer.order_id == order_id)
    if status is not None:
        stmt = stmt.where(OrderOffer.status == status)
    stmt = stmt.order_by(OrderOffer.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_offers_by_driver(
    db: AsyncSession,
    driver_id: int,
    status: Optional[OfferStatus] = None,
    skip: int = 0,
    limit: int = 20,
) -> Sequence[OrderOffer]:
    stmt = select(OrderOffer).where(OrderOffer.driver_id == driver_id)
    if status is not None:
        stmt = stmt.where(OrderOffer.status == status)
    stmt = stmt.offset(skip).limit(limit).order_by(OrderOffer.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_offer(
    db: AsyncSession,
    offer: OrderOffer,
    data: OrderOfferUpdate,
) -> OrderOffer:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(offer, field, value)
    await db.commit()
    await db.refresh(offer)
    return offer


async def update_offer_status(
    db: AsyncSession,
    offer: OrderOffer,
    status: OfferStatus,
) -> OrderOffer:
    offer.status = status
    await db.commit()
    await db.refresh(offer)
    return offer


async def accept_offer(
    db: AsyncSession,
    offer: OrderOffer,
) -> tuple[OrderOffer, Order]:
    """
    Bitta offerni qabul qilib, qolganlarini REJECTED qiladi
    va orderga driver tayinlaydi.
    """
    # Boshqa offerlarni reject qilish
    other_offers = await get_offers_for_order(db, offer.order_id)
    for other in other_offers:
        if other.id != offer.id:
            other.status = OfferStatus.REJECTED

    offer.status = OfferStatus.ACCEPTED

    # Orderni yangilash
    order_result = await db.execute(
        select(Order).where(Order.id == offer.order_id)
    )
    order = order_result.scalar_one()
    order.driver_id = offer.driver_id
    order.status = OrderStatus.ACCEPTED

    await db.commit()
    await db.refresh(offer)
    await db.refresh(order)
    return offer, order


async def delete_offer(db: AsyncSession, offer: OrderOffer) -> None:
    await db.delete(offer)
    await db.commit()