from driver.models import TruckType
from driver.schemas import TruckTypeCreate, TruckTypeUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Sequence, Optional

async def create(db: AsyncSession, data: TruckTypeCreate) -> TruckType:
    truck = TruckType(**data.model_dump())
    db.add(truck)
    try:
        await db.commit()
        await db.refresh(truck)
        return truck
    except Exception as exc:
        await db.rollback()
        raise exc


async def update(db: AsyncSession, pk: int, data: TruckTypeUpdate) -> Optional[TruckType]:
    result = await db.execute(select(TruckType).where(TruckType.id == pk))
    db_result = result.scalar_one_or_none()

    if not db_result:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_result, key, value)

    await db.commit()
    await db.refresh(db_result)
    return db_result


async def get_all(db: AsyncSession) -> Sequence[TruckType]:
    result = await db.execute(select(TruckType))
    db_result = result.scalars().all()
    return db_result


async def get_one(db: AsyncSession, pk: int) -> Optional[TruckType]:
    result = await db.execute(select(TruckType).where(TruckType.id == pk))

    return result.scalar_one_or_none()


async def delete(db: AsyncSession, pk: int) -> bool:
    result = await db.execute(select(TruckType).where(TruckType.id == pk))
    truck = result.scalar_one_or_none()

    if not truck:
        return False


    await db.delete(truck)

    try:
        await db.commit()
        return True
    except Exception as exc:
        await db.rollback()
        raise exc


