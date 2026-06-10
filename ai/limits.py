from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import AI_DAILY_LIMIT_FREE, AI_DAILY_LIMIT_PRO
from ai.models import AIUsage, AppSettings
from users.models import User, UserRole

logger = logging.getLogger(__name__)

_UNLIMITED = 10**9


def _today() -> date:
    return datetime.now(timezone.utc).date()


async def get_user_limit(db: AsyncSession, user: User) -> int:
    """User'ning kunlik so'rov chegarasi.

    ADMIN -> _UNLIMITED.
    AppSettings 'user_limit:{user_id}' bo'lsa shu.
    Aks holda user tariff (`free`/`pro`) asosida limit qaytaradi.
    """
    if user.role == UserRole.ADMIN:
        return _UNLIMITED

    override_row = await db.execute(
        select(AppSettings).where(AppSettings.key == f"user_limit:{user.id}")
    )
    override = override_row.scalar_one_or_none()
    if override:
        try:
            return int(override.value)
        except ValueError:
            logger.warning("Invalid user_limit value for %s: %s", user.id, override.value)

    tariff = await get_user_tariff(db, user.id)
    return AI_DAILY_LIMIT_PRO if tariff == "pro" else AI_DAILY_LIMIT_FREE


async def get_user_tariff(db: AsyncSession, user_id: int) -> str:
    """User tariff'ini qaytaradi: `free` yoki `pro`."""
    row = await db.execute(
        select(AppSettings).where(AppSettings.key == f"user_tariff:{user_id}")
    )
    setting = row.scalar_one_or_none()
    if setting and setting.value.strip().lower() in {"free", "pro"}:
        return setting.value.strip().lower()

    # Legacy support: eski `user_premium:{id}=true` bo'lsa pro deb qabul qilamiz.
    premium_row = await db.execute(
        select(AppSettings).where(AppSettings.key == f"user_premium:{user_id}")
    )
    premium = premium_row.scalar_one_or_none()
    if premium and premium.value.lower() in {"1", "true", "yes"}:
        return "pro"
    return "free"


async def _get_or_create_today_usage(db: AsyncSession, user_id: int) -> AIUsage:
    today = _today()
    result = await db.execute(
        select(AIUsage).where(AIUsage.user_id == user_id, AIUsage.usage_date == today)
    )
    usage = result.scalar_one_or_none()
    if usage is None:
        usage = AIUsage(
            user_id=user_id,
            usage_date=today,
            requests=0,
            input_tokens=0,
            output_tokens=0,
        )
        db.add(usage)
        await db.flush()
    return usage


async def check_request_quota(db: AsyncSession, user: User) -> Tuple[bool, int, int]:
    """Returns (allowed, used_today, limit). Hech qanday counter yangilanmaydi."""
    limit = await get_user_limit(db, user)
    if limit >= _UNLIMITED:
        usage = await _get_or_create_today_usage(db, user.id)
        await db.commit()
        return True, usage.requests, limit

    usage = await _get_or_create_today_usage(db, user.id)
    await db.commit()
    return usage.requests < limit, usage.requests, limit


async def increment_usage(
    db: AsyncSession,
    user_id: int,
    *,
    requests: int = 1,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> AIUsage:
    """Bugungi qatorni yangilaydi."""
    usage = await _get_or_create_today_usage(db, user_id)
    usage.requests += requests
    usage.input_tokens += int(input_tokens or 0)
    usage.output_tokens += int(output_tokens or 0)
    await db.commit()
    await db.refresh(usage)
    return usage


async def set_user_limit(db: AsyncSession, user_id: int, daily_requests: int) -> None:
    """AppSettings'da per-user override saqlash."""
    key = f"user_limit:{user_id}"
    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = str(daily_requests)
    else:
        db.add(AppSettings(key=key, value=str(daily_requests)))
    await db.commit()


async def set_user_tariff(db: AsyncSession, user_id: int, tariff: str) -> str:
    normalized = (tariff or "free").strip().lower()
    if normalized not in {"free", "pro"}:
        raise ValueError("tariff must be 'free' or 'pro'")

    key = f"user_tariff:{user_id}"
    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = normalized
    else:
        db.add(AppSettings(key=key, value=normalized))
    await db.commit()
    return normalized


async def get_usage_stats(
    db: AsyncSession,
    *,
    user_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[AIUsage]:
    stmt = select(AIUsage)
    if user_id is not None:
        stmt = stmt.where(AIUsage.user_id == user_id)
    if date_from is not None:
        stmt = stmt.where(AIUsage.usage_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(AIUsage.usage_date <= date_to)
    stmt = stmt.order_by(AIUsage.usage_date.desc(), AIUsage.user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def set_user_premium(db: AsyncSession, user_id: int, premium: bool) -> None:
    key = f"user_premium:{user_id}"
    result = await db.execute(select(AppSettings).where(AppSettings.key == key))
    row = result.scalar_one_or_none()
    val = "true" if premium else "false"
    if row:
        row.value = val
    else:
        db.add(AppSettings(key=key, value=val))
    await db.commit()
