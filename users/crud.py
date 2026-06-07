from typing import Optional

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from users.models import User, UserRole
from users.schemas import UserUpdate
from utils.validation import normalize_phone_number




async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_phone(db: AsyncSession, phone_number: str) -> Optional[User]:
    try:
        norm_phone = normalize_phone_number(phone_number)
        plus_less = norm_phone.lstrip('+')
    except Exception:
        norm_phone = phone_number
        plus_less = phone_number.lstrip('+') if phone_number.startswith('+') else phone_number

    result = await db.execute(
        select(User).where(
            or_(
                User.phone_number == norm_phone,
                User.phone_number == plus_less
            )
        )
    )
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()



async def update_user_role(db: AsyncSession, user: User, role: UserRole) -> User:
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user


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


async def delete_user(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.commit()


async def deactivate_user(db: AsyncSession, user: User) -> User:
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user

