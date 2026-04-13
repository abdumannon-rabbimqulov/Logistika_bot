from sqlalchemy import select, func, update

from config.config import async_session
from users.models import User

import driver.models  # noqa: F401
import order.models   # noqa: F401



async def get_user(user_id: int) -> User | None:
    """Foydalanuvchini Telegram ID bo'yicha topib qaytaradi."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()


async def create_user(
    user_id: int,
    full_name: str,
    username: str | None = None,
    language: str = "uz",
) -> User:
    """Yangi foydalanuvchi yaratib, bazaga saqlaydi."""
    async with async_session() as session:
        user = User(
            id=user_id,
            full_name=full_name,
            username=username,
            language=language,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def get_or_create_user(
    user_id: int,
    full_name: str,
    username: str | None = None,
    language: str = "uz",
) -> tuple[User, bool]:
    """
    Foydalanuvchini qaytaradi yoki yangi yaratadi.
    Return: (user, created) — created=True yangi yaratilganini bildiradi.
    """
    user = await get_user(user_id)
    if user:
        return user, False
    user = await create_user(user_id, full_name, username, language)
    return user, True


async def update_user_language(user_id: int, language: str) -> None:
    """Foydalanuvchi tilini bir so'rovda yangilaydi (Optimallashtirilgan)."""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(language=language)
        )
        await session.commit()


# --- Admin Functions ---

async def get_stats() -> dict:
    """Bot statistikasini qaytaradi."""
    async with async_session() as session:
        total_users = (await session.execute(select(func.count(User.id)))).scalar()
        drivers = (await session.execute(
            select(func.count(User.id)).where(User.role == "driver")
        )).scalar()
        customers = (await session.execute(
            select(func.count(User.id)).where(User.role == "customer")
        )).scalar()
        return {
            "total_users": total_users or 0,
            "drivers": drivers or 0,
            "customers": customers or 0,
            "others": (total_users or 0) - (drivers or 0) - (customers or 0)
        }


async def get_all_users(limit: int = 100) -> list[User]:
    """Barcha foydalanuvchilarni ro'yxatda qaytaradi."""
    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


async def ban_user(user_id: int) -> bool:
    """Foydalanuvchini bloklaydi."""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(is_banned=True)
        )
        await session.commit()
        return True


async def unban_user(user_id: int) -> bool:
    """Foydalanuvchi blokini ochadi."""
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(is_banned=False)
        )
        await session.commit()
        return True

