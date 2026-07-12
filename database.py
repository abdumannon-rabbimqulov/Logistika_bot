from sqlalchemy import select, func, update

from config.config import async_session
from users.models import User

import driver.models  # noqa: F401
import order.models   # noqa: F401



async def get_user(user_id: int) -> User | None:
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
    phone_number: str | None = None,
    role: str = "guest",
) -> User:
    async with async_session() as session:
        user = User(
            id=user_id,
            full_name=full_name,
            username=username,
            language=language,
            phone_number=phone_number,
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
    phone_number: str | None = None,
) -> tuple[User, bool]:

    user = await get_user(user_id)
    if user:
        return user, False
    user = await create_user(user_id, full_name, username, language, phone_number)
    return user, True


async def update_user_language(user_id: int, language: str) -> None:
    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(language=language)
        )
        await session.commit()


async def update_user_profile_from_tg(
    user_id: int,
    full_name: str,
    username: str | None,
    language: str,
    phone_number: str | None = None,
    role: str | None = None,
) -> None:
    values = {
        "full_name": full_name,
        "username": username,
        "language": language,
    }
    if phone_number:
        values["phone_number"] = phone_number
    if role:
        values["role"] = role

    async with async_session() as session:
        await session.execute(
            update(User).where(User.id == user_id).values(**values)
        )
        await session.commit()
