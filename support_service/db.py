"""Support bazasiga ulanish (asosiy ilovadagi `config/config.py` naqshi bo'yicha)."""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from support_service.config import SUPPORT_DB_URL

engine = create_async_engine(SUPPORT_DB_URL, echo=False, pool_pre_ping=True, pool_size=5, max_overflow=10)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
