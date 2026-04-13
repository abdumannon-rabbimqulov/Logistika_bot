from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import User
from schemas import UserUpdate


# ──────────────────────────────────────────────
#  READ
# ──────────────────────────────────────────────

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone_number: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.phone_number == phone_number)
    )
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


# ──────────────────────────────────────────────
#  UPDATE
# ──────────────────────────────────────────────

async def update_user(
    db: AsyncSession,
    user: User,
    data: UserUpdate,
) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


async def update_password(
    db: AsyncSession,
    user: User,
    new_hashed_password: str,
) -> User:
    user.password = new_hashed_password
    await db.commit()
    await db.refresh(user)
    return user


# ──────────────────────────────────────────────
#  DELETE
# ──────────────────────────────────────────────

async def delete_user(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.commit()


# ──────────────────────────────────────────────
#  DEACTIVATE  (o'chirish o'rniga faolsizlashtirish)
# ──────────────────────────────────────────────

async def deactivate_user(db: AsyncSession, user: User) -> User:
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user