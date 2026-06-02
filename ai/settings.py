from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select

from config.config import (
    MODEL_NAME,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    async_session,
)
from ai.models import AppSettings

logger = logging.getLogger(__name__)

_REDIS_KEY_MODEL = "ai:current_model"
_REDIS_TTL_SEC = 3600

try:
    import redis
    _redis_client = redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
    )
except Exception as exc:
    logger.warning("Redis client init failed, model cache disabled: %s", exc)
    _redis_client = None


def _redis_get(key: str) -> Optional[str]:
    if _redis_client is None:
        return None
    try:
        return _redis_client.get(key)
    except Exception as exc:
        logger.warning("Redis GET %s failed: %s", key, exc)
        return None


def _redis_set(key: str, value: str, ttl: int = _REDIS_TTL_SEC) -> None:
    if _redis_client is None:
        return
    try:
        _redis_client.setex(key, ttl, value)
    except Exception as exc:
        logger.warning("Redis SETEX %s failed: %s", key, exc)


async def get_current_model() -> str:
    cached = _redis_get(_REDIS_KEY_MODEL)
    if cached:
        return cached

    async with async_session() as db:
        result = await db.execute(
            select(AppSettings).where(AppSettings.key == "ai_model")
        )
        row = result.scalar_one_or_none()

    model = row.value if row else MODEL_NAME
    _redis_set(_REDIS_KEY_MODEL, model)
    return model


async def set_current_model(model: str) -> str:
    """Yangi model'ni saqlash (DB + Redis cache yangilash). Yangi qiymatni qaytaradi."""
    async with async_session() as db:
        result = await db.execute(
            select(AppSettings).where(AppSettings.key == "ai_model")
        )
        row = result.scalar_one_or_none()
        if row:
            row.value = model
        else:
            db.add(AppSettings(key="ai_model", value=model))
        await db.commit()

    _redis_set(_REDIS_KEY_MODEL, model)
    logger.info("AI model changed to: %s", model)
    return model


async def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Umumiy AppSettings olish (cache'siz, agar value uzun bo'lsa)."""
    async with async_session() as db:
        result = await db.execute(select(AppSettings).where(AppSettings.key == key))
        row = result.scalar_one_or_none()
    return row.value if row else default


async def set_setting(key: str, value: str) -> None:
    async with async_session() as db:
        result = await db.execute(select(AppSettings).where(AppSettings.key == key))
        row = result.scalar_one_or_none()
        if row:
            row.value = value
        else:
            db.add(AppSettings(key=key, value=value))
        await db.commit()
