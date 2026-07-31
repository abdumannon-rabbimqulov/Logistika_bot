"""RabbitMQ qatlami: haydovchi qidirish vazifalarini navbatga qo'yish.

Nega kerak edi: ilgari qidiruv (`services/dispatch.py`) HTTP so'rovning o'zida
bajarilardi — sender narxni oshirsa, javob qaytishidan oldin Redis'dan online
haydovchilar o'qilardi, DB'da nomzod tanlanardi va Telegram'ga xabar yuborilardi.
Buyurtmalar ko'payganda bu web jarayonini bo'g'ardi va hamma qidiruv bir vaqtda
ketardi. Endi API faqat "shu order uchun qidiruv kerak" degan xabarni qo'yadi,
og'ir ish esa `workers/dispatch_worker.py` da, `DISPATCH_PREFETCH` cheklovi bilan
bajariladi.

Topologiya (`declare_topology`, ikkala jarayonda ham idempotent chaqiriladi):

    logistika.dispatch (direct, durable)
        ├── "dispatch"       → dispatch.jobs     — worker shu navbatni o'qiydi
        └── "dispatch.dead"  → dispatch.dead     — qayta urinishlar tugagan xabarlar

    dispatch.delayed — kechiktirilgan yetkazish uchun (60s javob taymeri, xato
        bo'lganda backoff). Bu navbatning iste'molchisi YO'Q: `x-message-ttl`
        tugagach xabar dead-letter orqali `dispatch.jobs` ga o'zi tushadi. Shu
        bilan `asyncio.create_task` taymerlari o'rnini bosadi — jarayon qayta
        ishga tushsa ham taymer yo'qolmaydi.

Kutubxona `pika` emas, `aio-pika`: broker bir xil (AMQP 0-9-1), lekin loyiha
to'liq async — sinxron `pika` publish paytida event loop'ni bloklab qo'yardi.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import aio_pika
from aio_pika.abc import AbstractRobustChannel, AbstractRobustConnection, AbstractRobustExchange

from config.config import RABBITMQ_URL

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "logistika.dispatch"
JOBS_QUEUE = "dispatch.jobs"
DELAYED_QUEUE = "dispatch.delayed"
DEAD_QUEUE = "dispatch.dead"

ROUTING_KEY_JOBS = "dispatch"
ROUTING_KEY_DEAD = "dispatch.dead"

# Kechiktirilgan navbatning TTL'i (millisekund). Xabar shu muddat kutib, so'ng
# `dispatch.jobs` ga o'tadi. Bitta navbat bo'lgani uchun TTL ham bitta —
# `publish_dispatch_job(delay_sec=...)` xabar darajasidagi TTL bilan undan qisqa
# kechikish ham bera oladi, lekin navbat FIFO bo'lgani uchun oldidagi xabar
# tugamaguncha keyingisi chiqmaydi. Shuning uchun barcha kechikishlar shu
# qiymatga teng: 60s javob taymeri ham, backoff ham shundan kelib chiqib beriladi.
DELAY_TTL_MS = 62_000

_connection: Optional[AbstractRobustConnection] = None
_channel: Optional[AbstractRobustChannel] = None
_exchange: Optional[AbstractRobustExchange] = None
_lock = asyncio.Lock()


class QueueUnavailable(RuntimeError):
    """Broker bilan ishlab bo'lmadi (ulanish yo'q yoki publish muvaffaqiyatsiz)."""


async def get_channel() -> AbstractRobustChannel:
    """Jarayon uchun yagona (lazy) kanal. `connect_robust` uzilishda o'zi qayta ulanadi."""
    global _connection, _channel, _exchange

    if _channel is not None and not _channel.is_closed:
        return _channel

    async with _lock:
        # Qulfni kutib turgan ikkinchi chaqiruv uchun qayta tekshiriladi.
        if _channel is not None and not _channel.is_closed:
            return _channel
        try:
            if _connection is None or _connection.is_closed:
                _connection = await aio_pika.connect_robust(RABBITMQ_URL)
            _channel = await _connection.channel(publisher_confirms=True)
            _exchange = await _declare(_channel)
        except Exception as exc:  # ulanish/deklaratsiya xatosi
            _channel = None
            _exchange = None
            raise QueueUnavailable(f"RabbitMQ'ga ulanib bo'lmadi: {exc}") from exc
        return _channel


async def _declare(channel: AbstractRobustChannel) -> AbstractRobustExchange:
    exchange = await channel.declare_exchange(
        EXCHANGE_NAME, aio_pika.ExchangeType.DIRECT, durable=True
    )

    jobs = await channel.declare_queue(JOBS_QUEUE, durable=True)
    await jobs.bind(exchange, ROUTING_KEY_JOBS)

    dead = await channel.declare_queue(DEAD_QUEUE, durable=True)
    await dead.bind(exchange, ROUTING_KEY_DEAD)

    # Iste'molchisi yo'q navbat: TTL tugagach xabar dead-letter qoidasi bo'yicha
    # `logistika.dispatch` exchange'iga "dispatch" kaliti bilan qaytadi.
    await channel.declare_queue(
        DELAYED_QUEUE,
        durable=True,
        arguments={
            "x-message-ttl": DELAY_TTL_MS,
            "x-dead-letter-exchange": EXCHANGE_NAME,
            "x-dead-letter-routing-key": ROUTING_KEY_JOBS,
        },
    )
    return exchange


async def declare_topology() -> None:
    """Exchange/navbatlarni yaratadi (worker start'da va birinchi publish'da)."""
    await get_channel()


async def publish_dispatch_job(
    order_id: int,
    reason: str,
    *,
    delay: bool = False,
    attempt: int = 0,
    dead_letter: bool = False,
) -> None:
    """Qidiruv vazifasini navbatga qo'yadi.

    `reason` — faqat kuzatuv uchun ("created", "rejected", "expired", "price_bump",
    "retry"): worker baribir buyurtmaning DB'dagi joriy holatidan kelib chiqib
    ish tutadi, shuning uchun xabar mazmuni qaror qabul qilishga ta'sir qilmaydi.

    `delay=True` — xabar `dispatch.delayed` ga tushadi va ~`DELAY_TTL_MS` dan keyin
    ishlov navbatiga o'tadi (haydovchiga berilgan 60 soniya tugashini kutish uchun).

    Xabar `PERSISTENT` — broker qayta ishga tushsa ham yo'qolmaydi.
    """
    body = json.dumps(
        {"order_id": order_id, "reason": reason, "attempt": attempt},
        separators=(",", ":"),
    ).encode()

    message = aio_pika.Message(
        body=body,
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        message_id=f"{order_id}:{reason}:{attempt}",
    )

    try:
        channel = await get_channel()
        if delay:
            # Kechiktirilgan navbatga to'g'ridan-to'g'ri (default exchange, routing
            # key = navbat nomi) — u exchange'ga bog'lanmagan.
            await channel.default_exchange.publish(message, routing_key=DELAYED_QUEUE)
        else:
            routing_key = ROUTING_KEY_DEAD if dead_letter else ROUTING_KEY_JOBS
            await _exchange.publish(message, routing_key=routing_key)
    except QueueUnavailable:
        raise
    except Exception as exc:
        raise QueueUnavailable(f"Xabar yuborilmadi (order #{order_id}): {exc}") from exc


async def close_queue() -> None:
    """Ulanishni yopadi (FastAPI shutdown va worker to'xtashida)."""
    global _connection, _channel, _exchange
    try:
        if _connection is not None and not _connection.is_closed:
            await _connection.close()
    except Exception:
        logger.exception("RabbitMQ ulanishini yopishda xato")
    finally:
        _connection = None
        _channel = None
        _exchange = None
