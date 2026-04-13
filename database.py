from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import async_session
from users.models import User


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
    role: str = "guest",
) -> User:
    """Yangi foydalanuvchi yaratib, bazaga saqlaydi."""
    async with async_session() as session:
        user = User(
            id=user_id,
            full_name=full_name,
            username=username,
            language=language,
            role=role,
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
    Return: (user, created)  — created=True yangi yaratilganini bildiradi.
    """
    user = await get_user(user_id)
    if user:
        return user, False
    user = await create_user(user_id, full_name, username, language)
    return user, True


async def update_user_language(user_id: int, language: str) -> None:
    """Foydalanuvchi tilini yangilaydi."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.language = language
            await session.commit()


async def update_user_role(user_id: int, role: str) -> None:
    """Foydalanuvchi rolini yangilaydi."""
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            user.role = role
            await session.commit()
