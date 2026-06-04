"""Haydovchi jonli GPS: veb-sayt → Redis (tez) + Postgres (throttle) + admin pub/sub."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Dict, List, Optional

import redis.asyncio as aioredis
from redis.exceptions import RedisError
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
from services.datetime_utils import to_utc_naive, utc_now_naive
from users.models import User

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

    `live_period` veb-sayt yuborgan muddat (sekund); 0 bo'lsa default ishlatiladi.
    """
    now = utc_now_naive()
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

    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.set(_loc_key(driver_id), raw, ex=LIVE_LOC_TTL_SEC)
        pipe.sadd(ONLINE_SET, driver_id)
        pipe.publish(CHANNEL, raw)
        await pipe.execute()
    except (RedisError, OSError) as exc:
        logger.warning("Redis live location write failed, DB fallback used: %s", exc)
        await _persist_to_db(driver_id, lat, lon, expires_at)
        return payload

    await _maybe_persist_to_db(driver_id, lat, lon, expires_at)
    return payload


async def stop_driver_location(driver_id: int) -> None:
    """Driver live location'ni yopadi: Redis dan o'chiradi, DB ham yangilanadi."""
    try:
        r = get_redis()
        pipe = r.pipeline()
        pipe.delete(_loc_key(driver_id))
        pipe.srem(ONLINE_SET, driver_id)
        await pipe.execute()
    except (RedisError, OSError) as exc:
        logger.warning("Redis live location stop failed, DB fallback used: %s", exc)
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
    try:
        r = get_redis()
        flag = _dbsync_key(driver_id)
        set_ok = await r.set(flag, "1", ex=LIVE_LOC_DB_THROTTLE_SEC, nx=True)
        if not set_ok:
            return
    except (RedisError, OSError) as exc:
        logger.warning("Redis DB throttle failed, persisting directly: %s", exc)
    await _persist_to_db(driver_id, lat, lon, expires_at)


async def _persist_to_db(driver_id: int, lat: float, lon: float, expires_at: datetime) -> None:
    """Driver GPS snapshot'ini Postgres'ga yozadi."""
    expires_naive = to_utc_naive(expires_at)
    try:
        async with async_session() as db:
            await db.execute(
                update(Driver)
                .where(Driver.id == driver_id)
                .values(
                    last_latitude=float(lat),
                    last_longitude=float(lon),
                    last_location_at=utc_now_naive(),
                    is_live_location_active=True,
                    live_location_expires=expires_naive,
                )
            )
            await db.commit()
    except Exception as exc:
        logger.warning("DB sync for driver #%s failed: %s", driver_id, exc)


async def get_driver_location(driver_id: int) -> Optional[Dict]:
    try:
        r = get_redis()
        raw = await r.get(_loc_key(driver_id))
        if raw:
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
    except (RedisError, OSError) as exc:
        logger.warning("Redis get driver location failed, DB fallback used: %s", exc)

    rows = await _locations_from_db(driver_id=driver_id)
    return rows[0] if rows else None


async def get_all_online_drivers() -> List[Dict]:
    try:
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
    except (RedisError, OSError) as exc:
        logger.warning("Redis online drivers scan failed, DB fallback used: %s", exc)
        return await _locations_from_db()


async def _locations_from_db(driver_id: Optional[int] = None) -> List[Dict]:
    """Redis ishlamasa DB'dagi oxirgi GPS snapshotlardan fallback."""
    now = utc_now_naive()
    stmt = (
        select(Driver, User)
        .join(User, User.id == Driver.user_id)
        .where(
            Driver.is_live_location_active == True,  # noqa: E712
            Driver.last_latitude.is_not(None),
            Driver.last_longitude.is_not(None),
        )
    )
    if driver_id is not None:
        stmt = stmt.where(Driver.id == driver_id)
    stmt = stmt.where(
        (Driver.live_location_expires.is_(None)) | (Driver.live_location_expires > now)
    )

    try:
        async with async_session() as db:
            rows = (await db.execute(stmt)).all()
    except Exception as exc:
        logger.warning("DB fallback locations failed: %s", exc)
        return []

    result: List[Dict] = []
    for driver, user in rows:
        result.append(
            {
                "driver_id": driver.id,
                "user_id": driver.user_id,
                "full_name": user.full_name,
                "truck_number": driver.truck_number,
                "truck_type_id": driver.truck_type_id,
                "lat": float(driver.last_latitude),
                "lon": float(driver.last_longitude),
                "ts": (driver.last_location_at or datetime.now(timezone.utc)).isoformat(),
                "expires_at": (
                    driver.live_location_expires.isoformat()
                    if driver.live_location_expires
                    else None
                ),
            }
        )
    return result


async def subscribe_location_updates() -> AsyncIterator[Dict]:
    """Async generator — pub/sub orqali kelgan driver location yangilanishlari."""
    try:
        r = get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(CHANNEL)
    except (RedisError, OSError) as exc:
        logger.warning("Redis pub/sub unavailable: %s", exc)
        return
    try:
        while True:
            try:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30)
            except (RedisError, OSError) as exc:
                logger.warning("Redis pub/sub read failed: %s", exc)
                break
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
