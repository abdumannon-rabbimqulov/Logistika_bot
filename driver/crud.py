from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional, Sequence
from driver.models import (
    TruckType, Driver,
)
from order.models import Order, OrderStatus
from driver.schemas import (
    TruckTypeCreate, TruckTypeUpdate,
    DriverCreate, DriverUpdate
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
