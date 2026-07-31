import json
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import AsyncGenerator, Dict, Any, List, Optional
import redis.asyncio as aioredis

from config.config import REDIS_HOST

logger = logging.getLogger(__name__)

# Redis configuration
# We use the config value or fallback to defaults
REDIS_PORT = 6379

redis_client: Optional[aioredis.Redis] = None

def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        url = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
        redis_client = aioredis.from_url(url, decode_responses=True)
    return redis_client

async def close_redis() -> None:
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None

async def claim_notice_slot(key: str, ttl_seconds: int) -> bool:
    """Takroriy bildirishnomalarni cheklash uchun: `True` — hozir yuborish mumkin.

    Redis'da `SET key 1 NX EX ttl` — kalit band bo'lsa `False` qaytadi, ya'ni shu
    haydovchiga yaqinda allaqachon xabar yuborilgan (spamning oldini oladi).
    Redis ishlamay qolsa `False` qaytadi — bildirishnoma yuborilmaydi, lekin
    dispatch oqimi buzilmaydi.
    """
    try:
        r = get_redis()
        return bool(await r.set(key, "1", nx=True, ex=ttl_seconds))
    except Exception:
        logger.exception("Bildirishnoma cheklovini tekshirib bo'lmadi: %s", key)
        return False


async def acquire_lock(key: str, ttl_seconds: int) -> bool:
    """Qisqa muddatli qulf: `True` — qulf shu chaqiruvda olindi.

    `claim_notice_slot` bilan bir xil `SET NX EX`, lekin XATO PAYTIDAGI xulqi teskari:
    Redis ishlamay qolsa `True` qaytadi ("fail-open"). Sabab — bu qulf faqat bir xil
    vazifa ikki marta yetkazilganda ortiqcha ish qilmaslik uchun optimallashtirish;
    to'g'rilikni baribir DB holati ta'minlaydi (`status`/`driver_id` tekshiruvi va
    `UPDATE ... WHERE status='pending'`). Redis o'chgani uchun qidiruvni butunlay
    to'xtatib qo'yish esa buyurtmalarni haydovchisiz qoldirardi.
    """
    try:
        r = get_redis()
        return bool(await r.set(key, "1", nx=True, ex=ttl_seconds))
    except Exception:
        logger.exception("Qulfni olishda xato (fail-open): %s", key)
        return True


async def release_lock(key: str) -> None:
    """Qulfni muddatidan oldin bo'shatadi (vazifa tugagach)."""
    try:
        await get_redis().delete(key)
    except Exception:
        logger.exception("Qulfni bo'shatishda xato: %s", key)


def _current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _future_utc_iso(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()

async def update_driver_location(
    driver_id: int,
    lat: float,
    lon: float,
    user_id: int,
    full_name: str,
    truck_number: str,
    truck_type_id: int,
    live_period: int = 1800,
    accuracy: Optional[float] = None,
) -> None:
    """Haydovchining GPS kordinatasini yangilash.

    `accuracy` (metr) — ixtiyoriy: geofence tekshiruvi bu nuqtani zaxira sifatida
    ishlatganda ruxsat etilgan radiusni aniqlikka qarab kengaytiradi
    (services/geofence.py). Eski klientlar uni yubormaydi — shunda `None` qoladi.
    """
    try:
        r = get_redis()
        key = f"driver_location:{driver_id}"
        ts = _current_utc_iso()
        expires_at = _future_utc_iso(live_period)
        
        payload = {
            "driver_id": driver_id,
            "user_id": user_id,
            "full_name": full_name,
            "truck_number": truck_number,
            "truck_type_id": truck_type_id,
            "lat": lat,
            "lon": lon,
            "accuracy": accuracy,
            "ts": ts,
            "expires_at": expires_at,
        }
        
        data_str = json.dumps(payload)
        
        # Redisda saqlash (vaqti bilan o'chib ketadi)
        await r.set(key, data_str, ex=live_period)
        
        # Obunachilarga (adminlarga/xaridorlarga) xabar yuborish
        await r.publish("driver_locations_channel", data_str)
    except Exception as e:
        logger.error(f"Error updating driver location for driver {driver_id}: {e}")

async def stop_driver_location(driver_id: int) -> None:
    """Haydovchining jonli lokatsiyasini to'xtatish."""
    try:
        r = get_redis()
        key = f"driver_location:{driver_id}"
        await r.delete(key)
        
        # Obunachilarga to'xtaganligini bildirish uchun bo'sh (yoki to'xtatilganligini bildiruvchi) ma'lumot yuborish
        ts = _current_utc_iso()
        payload = {
            "driver_id": driver_id,
            "lat": 0.0,
            "lon": 0.0,
            "ts": ts,
            "expires_at": ts, # Hozirgi vaqt
            "stopped": True
        }
        await r.publish("driver_locations_channel", json.dumps(payload))
    except Exception as e:
        logger.error(f"Error stopping driver location for driver {driver_id}: {e}")

async def get_driver_location(driver_id: int) -> Optional[Dict[str, Any]]:
    """Alohida bitta haydovchining oxirgi lokatsiyasini olish."""
    try:
        r = get_redis()
        key = f"driver_location:{driver_id}"
        data = await r.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.error(f"Error getting driver location for driver {driver_id}: {e}")
        return None

async def get_all_online_drivers() -> List[Dict[str, Any]]:
    """Barcha online (jonli translyatsiya qilayotgan) haydovchilarni olish.

    KEYS o'rniga SCAN ishlatiladi — KEYS butun Redis'ni bloklaydi va
    production'da kalitlar ko'payganda serverni sekinlashtiradi.
    """
    try:
        r = get_redis()
        keys: List[str] = []
        async for key in r.scan_iter(match="driver_location:*", count=500):
            keys.append(key)
        if not keys:
            return []

        values = await r.mget(keys)
        drivers = []
        for val in values:
            if val:
                drivers.append(json.loads(val))
        return drivers
    except Exception as e:
        logger.error(f"Error getting all online drivers: {e}")
        return []

async def subscribe_location_updates() -> AsyncGenerator[Dict[str, Any], None]:
    """Redis orqali yangilangan lokatsiyalarni kanal orqali tinglash (Generator)."""
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe("driver_locations_channel")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    payload = json.loads(message["data"])
                    yield payload
                except json.JSONDecodeError:
                    continue
    finally:
        await pubsub.unsubscribe("driver_locations_channel")
        await pubsub.close()
