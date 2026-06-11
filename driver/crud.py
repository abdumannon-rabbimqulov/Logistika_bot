from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Sequence
from driver.models import (
    TruckType, Driver,
    DriverAnnouncement, AnnouncementWaypoint, AnnouncementOffer
)
from order.models import Order, OrderStatus
from order.crud import sort_order_waypoints
from driver.schemas import (
    TruckTypeCreate, TruckTypeUpdate,
    DriverCreate, DriverUpdate,
    DriverAnnouncementCreate, DriverAnnouncementUpdate,
    AnnouncementOfferCreate, AnnouncementOfferUpdate,
)


async def create_truck_type(db: AsyncSession, data: TruckTypeCreate) -> TruckType:
    obj = TruckType(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_truck_type(db: AsyncSession, pk: int) -> Optional[TruckType]:
    result = await db.execute(select(TruckType).where(TruckType.id == pk))
    return result.scalar_one_or_none()

async def get_all_truck_types(db: AsyncSession) -> List[TruckType]:
    result = await db.execute(select(TruckType))
    return result.scalars().all()

async def update_truck_type(db: AsyncSession, pk: int, data: TruckTypeUpdate) -> Optional[TruckType]:
    await db.execute(update(TruckType).where(TruckType.id == pk).values(**data.model_dump(exclude_unset=True)))
    await db.commit()
    return await get_truck_type(db, pk)

async def delete_truck_type(db: AsyncSession, pk: int) -> bool:
    await db.execute(delete(TruckType).where(TruckType.id == pk))
    await db.commit()
    return True


async def create_driver(db: AsyncSession, data: DriverCreate, *, user_id: int) -> Driver:
    payload = data.model_dump(exclude={"phone_number"})
    obj = Driver(user_id=user_id, **payload)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_driver(db: AsyncSession, pk: int) -> Optional[Driver]:
    result = await db.execute(select(Driver).where(Driver.id == pk))
    return result.scalar_one_or_none()

async def get_driver_by_user_id(db: AsyncSession, user_id: int) -> Optional[Driver]:
    result = await db.execute(select(Driver).where(Driver.user_id == user_id))
    return result.scalar_one_or_none()

async def get_all_drivers(db: AsyncSession) -> List[Driver]:
    result = await db.execute(select(Driver))
    return result.scalars().all()

async def update_driver(db: AsyncSession, pk: int, data: DriverUpdate) -> Optional[Driver]:
    await db.execute(update(Driver).where(Driver.id == pk).values(**data.model_dump(exclude_unset=True)))
    await db.commit()
    return await get_driver(db, pk)


def format_balance_uzs(amount) -> str:
    """Masalan: 1200000 -> '1 200 000 UZS'."""
    from decimal import Decimal

    value = int(Decimal(str(amount)))
    formatted = f"{value:,}".replace(",", " ")
    return f"{formatted} UZS"


_TRIP_SCOPE_STATUSES: dict[str, Sequence[OrderStatus]] = {
    "current": (OrderStatus.ACCEPTED, OrderStatus.IN_PROGRESS),
    "completed": (OrderStatus.COMPLETED,),
    "all": (
        OrderStatus.ACCEPTED,
        OrderStatus.IN_PROGRESS,
        OrderStatus.COMPLETED,
        OrderStatus.CANCELLED,
    ),
}


async def get_driver_trips(
    db: AsyncSession,
    driver_id: int,
    *,
    scope: str = "all",
    skip: int = 0,
    limit: int = 50,
) -> tuple[List[Order], int]:
    """Haydovchiga biriktirilgan safarlar (buyurtmalar)."""
    statuses = _TRIP_SCOPE_STATUSES.get(scope, _TRIP_SCOPE_STATUSES["all"])

    from driver.models import Driver
    base = (
        select(Order)
        .options(
            selectinload(Order.waypoints),
            selectinload(Order.customer),
            selectinload(Order.driver).selectinload(Driver.user)
        )
        .where(Order.driver_id == driver_id, Order.status.in_(statuses))
    )

    from sqlalchemy import func

    total = (
        await db.execute(
            select(func.count(Order.id)).where(
                Order.driver_id == driver_id,
                Order.status.in_(statuses),
            )
        )
    ).scalar_one()

    stmt = (
        base.order_by(desc(Order.updated_at))
        .offset(max(skip, 0))
        .limit(min(max(limit, 1), 100))
    )
    result = await db.execute(stmt)
    orders = [sort_order_waypoints(o) for o in result.scalars().all()]
    return orders, total






async def create_announcement(db: AsyncSession, data: DriverAnnouncementCreate) -> DriverAnnouncement:
    waypoints_data = data.waypoints
    ann_dict = data.model_dump()
    del ann_dict['waypoints']
    
    obj = DriverAnnouncement(**ann_dict)
    db.add(obj)
    await db.flush()
    
    for wp_data in waypoints_data:
        wp = AnnouncementWaypoint(announcement_id=obj.id, **wp_data.model_dump())
        db.add(wp)
    
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_announcement(db: AsyncSession, pk: int) -> Optional[DriverAnnouncement]:
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(DriverAnnouncement)
        .options(selectinload(DriverAnnouncement.waypoints))
        .where(DriverAnnouncement.id == pk)
    )
    return result.scalar_one_or_none()

async def get_all_announcements(db: AsyncSession, driver_id: Optional[int] = None) -> List[DriverAnnouncement]:
    from sqlalchemy.orm import selectinload
    stmt = select(DriverAnnouncement).options(selectinload(DriverAnnouncement.waypoints))
    if driver_id:
        stmt = stmt.where(DriverAnnouncement.driver_id == driver_id)
    result = await db.execute(stmt)
    return result.scalars().all()

async def update_announcement(db: AsyncSession, pk: int, data: DriverAnnouncementUpdate) -> Optional[DriverAnnouncement]:
    await db.execute(update(DriverAnnouncement).where(DriverAnnouncement.id == pk).values(**data.model_dump(exclude_unset=True)))
    await db.commit()
    return await get_announcement(db, pk)


async def create_announcement_offer(db: AsyncSession, data: AnnouncementOfferCreate) -> AnnouncementOffer:
    obj = AnnouncementOffer(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def get_announcement_offer(db: AsyncSession, pk: int) -> Optional[AnnouncementOffer]:
    result = await db.execute(select(AnnouncementOffer).where(AnnouncementOffer.id == pk))
    return result.scalar_one_or_none()


async def get_announcement_offers(db: AsyncSession, announcement_id: int) -> List[AnnouncementOffer]:
    result = await db.execute(select(AnnouncementOffer).where(AnnouncementOffer.announcement_id == announcement_id))
    return result.scalars().all()

async def update_announcement_offer(db: AsyncSession, pk: int, data: AnnouncementOfferUpdate) -> Optional[AnnouncementOffer]:
    update_data = data.model_dump(exclude_unset=True)
    if 'counter_price' in update_data:
        from datetime import datetime, timezone
        update_data['counter_at'] = datetime.now(timezone.utc)
    
    await db.execute(update(AnnouncementOffer).where(AnnouncementOffer.id == pk).values(**update_data))
    await db.commit()
    return await get_announcement_offer(db, pk)
