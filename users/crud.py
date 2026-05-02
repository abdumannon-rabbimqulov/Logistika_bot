from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from users.models import User, UserRole
from users.schemas import UserUpdate




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


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Email manzili bo'yicha foydalanuvchini qidiradi."""
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def create_user_by_email(
    db: AsyncSession,
    *,
    full_name: str,
    email: str,
    hashed_password: str,
    username: Optional[str] = None,
    language: str = "uz",
) -> User:
    """
    Email va parol orqali yangi foydalanuvchi yaratadi.
    ID avtomatik generatsiya qilinadi (Telegram ID kerak emas).
    """
    import hashlib, time
    unique_id = int(hashlib.md5(f"{email}{time.time()}".encode()).hexdigest(), 16) % (10**15)

    user = User(
        id=unique_id,
        full_name=full_name,
        email=email,
        password=hashed_password,
        username=username,
        language=language,
        role=UserRole.GUEST,
        is_active=True,
        is_banned=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_role(db: AsyncSession, user: User, role: UserRole) -> User:
    """Foydalanuvchi rolini yangilaydi."""
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

