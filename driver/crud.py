from driver.models import Driver, TruckType
from driver.schemas import TruckTypeCreate, TruckTypeUpdate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Sequence, Optional


# ═══════════════════════════════════════════════════════════════════════════
# DRIVER CRUD
# ═══════════════════════════════════════════════════════════════════════════

async def get_driver_by_user_id(db: AsyncSession, user_id: int) -> Optional[Driver]:
    """User ID orqali driver profilini topadi."""
    result = await db.execute(
        select(Driver).where(Driver.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_driver(
    db: AsyncSession,
    *,
    user_id: int,
    truck_type_id: int,
    truck_number: str,
    current_city: str,
    truck_brand: Optional[str] = None,
    truck_year: Optional[int] = None,
    capacity_ton: Optional[float] = None,
    capacity_m3: Optional[float] = None,
) -> Driver:
    """
    Ro'yxatdan o'tish uchun driver profili yaratadi.
    Hujjatlar va boshqa tafsilotlar keyinroq qo'shiladi.
    """
    driver = Driver(
        user_id=user_id,
        truck_type_id=truck_type_id,
        truck_number=truck_number,
        current_city=current_city,
        truck_brand=truck_brand,
        truck_year=truck_year,
        capacity_ton=capacity_ton,
        capacity_m3=capacity_m3,
        is_available=True,
        docs_verified=False,
        is_blocked=False,
    )
    db.add(driver)
    try:
        await db.commit()
        await db.refresh(driver)
        return driver
    except Exception as exc:
        await db.rollback()
        raise exc


# ═══════════════════════════════════════════════════════════════════════════
# TRUCK TYPE CRUD
# ═══════════════════════════════════════════════════════════════════════════

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
