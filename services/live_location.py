"""Driver live location oqimi: Redis (asyncio) + Postgres throttle.

- Telegram bot driver yuborgan har bir live-location yangilanishini
  `update_driver_location()` ga uzatadi.
- Redis kalit konvensiyasi:
    - `live:loc:driver:{driver_id}` -> JSON, TTL = LIVE_LOC_TTL_SEC (sliding)
    - `live:online:drivers`         -> SET (driver_id'lar)
    - Pub/Sub channel: `live:loc:updates`
- DB sinxronizatsiyasi (Driver.last_*) `LIVE_LOC_DB_THROTTLE_SEC` (default 60s)
  bo'yicha throttle qilinadi: `live:loc:driver:{id}:dbsync` flag kaliti.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Dict, List, Optional

import redis.asyncio as aioredis
from sqlalchemy import select, update

from config.config import (
    LIVE_LOC_DB_THROTTLE_SEC,
    LIVE_LOC_DEFAULT_PERIOD_SEC,
    LIVE_LOC_TTL_SEC,
    REDIS_DB,
    REDIS_HOST,
    REDIS_PORT,
    async_session,
)
from driver.models import Driver

logger = logging.getLogger(__name__)


CHANNEL = "live:loc:updates"
ONLINE_SET = "live:online:drivers"


def _loc_key(driver_id: int) -> str:
    return f"live:loc:driver:{driver_id}"


def _dbsync_key(driver_id: int) -> str:
    return f"live:loc:driver:{driver_id}:dbsync"


_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """Lazy singleton async Redis client."""
    global _redis
    if _redis is None:
        _redis = aioredis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
        )
    return _redis


async def update_driver_location(
    *,
    driver_id: int,
    lat: float,
    lon: float,
    user_id: Optional[int] = None,
    full_name: Optional[str] = None,
    truck_number: Optional[str] = None,
    truck_type_id: Optional[int] = None,
    live_period: int = 0,
) -> Dict:
    """Yangi koordinatani Redis'ga yozadi, broadcast qiladi va periodik DB'ga sinxronlaydi.

    `live_period` Telegram tomonidan berilgan masofa (soniya); 0 bo'lsa default ishlatiladi.
    """
    r = get_redis()
    now = datetime.now(timezone.utc)
    period = live_period if live_period and live_period > 0 else LIVE_LOC_DEFAULT_PERIOD_SEC
    expires_at = now + timedelta(seconds=period)

    payload: Dict = {
        "driver_id": int(driver_id),
        "user_id": int(user_id) if user_id is not None else None,
        "full_name": full_name,
        "truck_number": truck_number,
        "truck_type_id": int(truck_type_id) if truck_type_id is not None else None,
        "lat": float(lat),
        "lon": float(lon),
        "ts": now.isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    raw = json.dumps(payload, default=str)

    pipe = r.pipeline()
    pipe.set(_loc_key(driver_id), raw, ex=LIVE_LOC_TTL_SEC)
    pipe.sadd(ONLINE_SET, driver_id)
    pipe.publish(CHANNEL, raw)
    await pipe.execute()

    await _maybe_persist_to_db(driver_id, lat, lon, expires_at)
    return payload


async def stop_driver_location(driver_id: int) -> None:
    """Driver live location'ni yopadi: Redis dan o'chiradi, DB ham yangilanadi."""
    r = get_redis()
    pipe = r.pipeline()
    pipe.delete(_loc_key(driver_id))
    pipe.srem(ONLINE_SET, driver_id)
    await pipe.execute()
    try:
        async with async_session() as db:
            await db.execute(
                update(Driver)
                .where(Driver.id == driver_id)
                .values(is_live_location_active=False)
            )
            await db.commit()
    except Exception as exc:
        logger.warning("stop_driver_location DB update failed for #%s: %s", driver_id, exc)


async def _maybe_persist_to_db(
    driver_id: int, lat: float, lon: float, expires_at: datetime
) -> None:
    """Har LIVE_LOC_DB_THROTTLE_SEC sekundda bir marta DB'ga snapshot."""
    r = get_redis()
    flag = _dbsync_key(driver_id)
    set_ok = await r.set(flag, "1", ex=LIVE_LOC_DB_THROTTLE_SEC, nx=True)
    if not set_ok:
        return
    try:
        async with async_session() as db:
            await db.execute(
                update(Driver)
                .where(Driver.id == driver_id)
                .values(
                    last_latitude=float(lat),
                    last_longitude=float(lon),
                    last_location_at=datetime.now(timezone.utc),
                    is_live_location_active=True,
                    live_location_expires=expires_at,
                )
            )
            await db.commit()
    except Exception as exc:
        logger.warning("DB sync for driver #%s failed: %s", driver_id, exc)


async def get_driver_location(driver_id: int) -> Optional[Dict]:
    r = get_redis()
    raw = await r.get(_loc_key(driver_id))
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


async def get_all_online_drivers() -> List[Dict]:
    r = get_redis()
    items: List[Dict] = []
    async for key in r.scan_iter(match="live:loc:driver:*", count=200):
        if key.endswith(":dbsync"):
            continue
        raw = await r.get(key)
        if not raw:
            continue
        try:
            items.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return items


async def subscribe_location_updates() -> AsyncIterator[Dict]:
    """Async generator — pub/sub orqali kelgan driver location yangilanishlari."""
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(CHANNEL)
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
            if msg is None:
                await asyncio.sleep(0)
                continue
            data = msg.get("data")
            if not data:
                continue
            try:
                yield json.loads(data)
            except json.JSONDecodeError:
                logger.debug("Invalid pub/sub payload: %r", data)
                continue
    finally:
        try:
            await pubsub.unsubscribe(CHANNEL)
        except Exception:
            pass
        try:
            await pubsub.close()
        except Exception:
            pass
