from sqlalchemy import select, func, update

from config.config import async_session
from users.models import User

import driver.models  # noqa: F401
import order.models   # noqa: F401



from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from config.config import async_session
from users.models import User
import logging

import driver.models  # noqa: F401
import order.models   # noqa: F401

# Logger sozlash
logger = logging.getLogger(__name__)

async def get_user(user_id: int, session: AsyncSession | None = None) -> User | None:
    """
    Foydalanuvchini Telegram ID bo'yicha bazadan qidiradi.
    
    :param user_id: Telegram foydalanuvchi IDsi
    :param session: SQLAlchemy AsyncSession (ixtiyoriy)
    :return: User obyekti yoki None
    """
    if session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


async def update_user_token(
    user_id: int, 
    token: str, 
    expires: datetime, 
    session: AsyncSession | None = None
) -> None:
    """Foydalanuvchi tokenini yangilaydi."""
    stmt = update(User).where(User.id == user_id).values(
        token=token, 
        token_expires=expires
    )
    if session:
        await session.execute(stmt)
        return

    async with async_session() as session:
        try:
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating token for {user_id}: {e}")


async def create_user(
    user_id: int,
    full_name: str,
    username: str | None = None,
    language: str = "uz",
    session: AsyncSession | None = None
) -> User:
    """
    Yangi foydalanuvchi yaratadi.
    """
    user = User(
        id=user_id,
        full_name=full_name,
        username=username,
        language=language,
    )
    
    if session:
        session.add(user)
        await session.flush() # ID va boshqa avtomatik maydonlarni olish uchun
        return user

    async with async_session() as session:
        try:
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
        except Exception as e:
            await session.rollback()
            logger.error(f"Error creating user {user_id}: {e}")
            raise


async def update_user_language(user_id: int, language: str, session: AsyncSession | None = None) -> None:
    """Foydalanuvchi tilini yangilaydi."""
    stmt = update(User).where(User.id == user_id).values(language=language)
    if session:
        await session.execute(stmt)
        return

    async with async_session() as session:
        try:
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating language for {user_id}: {e}")


async def update_user_phone(user_id: int, phone_number: str, session: AsyncSession | None = None) -> None:
    """Foydalanuvchi telefon raqamini yangilaydi."""
    stmt = update(User).where(User.id == user_id).values(phone_number=phone_number)
    if session:
        await session.execute(stmt)
        return

    async with async_session() as session:
        try:
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating phone for {user_id}: {e}")


# --- Admin Functions ---

async def get_stats(session: AsyncSession | None = None) -> dict:
    """
    Bot statistikasini bitta so'rovda hisoblab qaytaradi.
    (Optimallashtirilgan: Multiple counts in one query)
    """
    query = select(
        func.count(User.id).label("total"),
        func.count(User.id).filter(User.role == "driver").label("drivers"),
        func.count(User.id).filter(User.role == "customer").label("customers")
    )
    
    async def execute_query(s: AsyncSession):
        res = await s.execute(query)
        row = res.one()
        return {
            "total_users": row.total or 0,
            "drivers": row.drivers or 0,
            "customers": row.customers or 0,
            "others": (row.total or 0) - (row.drivers or 0) - (row.customers or 0)
        }

    if session:
        return await execute_query(session)

    async with async_session() as session:
        return await execute_query(session)


async def get_all_users(limit: int = 100, session: AsyncSession | None = None) -> list[User]:
    """Barcha foydalanuvchilarni ro'yxatda qaytaradi."""
    stmt = select(User).order_by(User.created_at.desc()).limit(limit)
    if session:
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async with async_session() as session:
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def ban_user(user_id: int, session: AsyncSession | None = None) -> bool:
    """Foydalanuvchini bloklaydi."""
    stmt = update(User).where(User.id == user_id).values(is_banned=True)
    if session:
        res = await session.execute(stmt)
        return res.rowcount > 0

    async with async_session() as session:
        try:
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount > 0
        except Exception:
            await session.rollback()
            return False


async def unban_user(user_id: int, session: AsyncSession | None = None) -> bool:
    """Foydalanuvchi blokini ochadi."""
    stmt = update(User).where(User.id == user_id).values(is_banned=False)
    if session:
        res = await session.execute(stmt)
        return res.rowcount > 0

    async with async_session() as session:
        try:
            res = await session.execute(stmt)
            await session.commit()
            return res.rowcount > 0
        except Exception:
            await session.rollback()
            return False

