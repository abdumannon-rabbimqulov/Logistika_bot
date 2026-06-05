from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from order.models import District, Region


def _ilike(term: str) -> str:
    return f"%{term.strip()}%"


async def search_regions(db: AsyncSession, q: Optional[str] = None, limit: int = 50) -> List[Region]:
    stmt = select(Region).order_by(Region.name_uz)
    if q and q.strip():
        pattern = _ilike(q)
        stmt = stmt.where(
            or_(
                Region.name_uz.ilike(pattern),
                Region.name_ru.ilike(pattern),
                Region.name_en.ilike(pattern),
            )
        )
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_region(db: AsyncSession, pk: int) -> Optional[Region]:
    result = await db.execute(select(Region).where(Region.id == pk))
    return result.scalar_one_or_none()


async def search_districts(
    db: AsyncSession,
    region_id: int,
    q: Optional[str] = None,
    limit: int = 100,
) -> List[District]:
    stmt = (
        select(District)
        .where(District.region_id == region_id)
        .order_by(District.name_uz)
    )
    if q and q.strip():
        pattern = _ilike(q)
        stmt = stmt.where(
            or_(
                District.name_uz.ilike(pattern),
                District.name_ru.ilike(pattern),
                District.name_en.ilike(pattern),
            )
        )
    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_district(db: AsyncSession, pk: int) -> Optional[District]:
    result = await db.execute(
        select(District)
        .options(selectinload(District.region))
        .where(District.id == pk)
    )
    return result.scalar_one_or_none()
