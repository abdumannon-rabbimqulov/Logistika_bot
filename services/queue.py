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

Ikkinchi topologiya — `logistika.events` (topic, `EVENTS_*` konstantalari):
mikroservizlar o'rtasidagi biznes hodisalari. Farqi shundaki `dispatch` — bu
"shu ishni bajar" degan VAZIFA (bitta iste'molchi oladi), `events` esa "shunday
bo'ldi" degan XABAR: uni nechta xizmat tinglashi oldindan noma'lum, shuning uchun
topic exchange va har bir iste'molchi uchun alohida navbat.

    logistika.events (topic, durable)
        ├── order.status_changed  ─┬→ support.order_events   (support_service o'qiydi)
        ├── order.truck_assigned  ─┘
        ├── support.ticket_created ─┬→ support.notifications (workers/events_worker.py o'qiydi)
        └── support.ticket_replied ─┘
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

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

# --- Biznes hodisalari (mikroservizlararo) ---------------------------------

EVENTS_EXCHANGE = "logistika.events"

# Routing key'lar SHARTNOMA: ularni o'zgartirish support mikroservizini ham
# buzadi, shuning uchun `tests/test_event_contract.py` ularni qotirib qo'ygan.
EVENT_ORDER_STATUS_CHANGED = "order.status_changed"
EVENT_ORDER_TRUCK_ASSIGNED = "order.truck_assigned"
EVENT_SUPPORT_TICKET_CREATED = "support.ticket_created"
EVENT_SUPPORT_TICKET_REPLIED = "support.ticket_replied"

# Support mikroservizi buyurtma hodisalarini tinglaydi (ochiq murojaatlarga
# "buyurtma holati o'zgardi" degan tizim izohini qo'shish uchun).
SUPPORT_EVENTS_QUEUE = "support.order_events"
SUPPORT_EVENTS_PATTERN = "order.*"

# Asosiy ilova esa support hodisalarini tinglaydi (adminlarga bildirishnoma).
SUPPORT_NOTIFICATIONS_QUEUE = "support.notifications"
SUPPORT_NOTIFICATIONS_PATTERN = "support.*"

_events_exchange: Optional[AbstractRobustExchange] = None

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
    global _connection, _channel, _exchange, _events_exchange

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
            _events_exchange = None
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

    await _declare_events(channel)
    return exchange


async def _declare_events(channel: AbstractRobustChannel) -> AbstractRobustExchange:
    """Hodisalar topologiyasi. Idempotent — har bir jarayon startda chaqiradi.

    Navbatlar shu yerda (asosiy ilovada) e'lon qilinadi, iste'molchi hali
    ko'tarilmagan bo'lsa ham: aks holda support konteyneri kechikib ishga tushsa,
    o'sha oraliqda chiqqan hodisalar hech qayerga tushmay yo'qolardi.
    """
    global _events_exchange

    exchange = await channel.declare_exchange(
        EVENTS_EXCHANGE, aio_pika.ExchangeType.TOPIC, durable=True
    )

    support_events = await channel.declare_queue(SUPPORT_EVENTS_QUEUE, durable=True)
    await support_events.bind(exchange, SUPPORT_EVENTS_PATTERN)

    notifications = await channel.declare_queue(SUPPORT_NOTIFICATIONS_QUEUE, durable=True)
    await notifications.bind(exchange, SUPPORT_NOTIFICATIONS_PATTERN)

    _events_exchange = exchange
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


async def declare_events_topology() -> None:
    """Faqat hodisalar topologiyasini e'lon qiladi (`declare_topology` uni ham qamrab oladi)."""
    await get_channel()


def build_event(event: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Hodisa konverti — barcha xabarlar bir xil ko'rinishda bo'lishi uchun.

    `event_id` iste'molchiga takroriy yetkazishni (at-least-once) aniqlash imkonini
    beradi, `occurred_at` esa xabar navbatda kutib qolganda ham hodisaning haqiqiy
    vaqtini saqlaydi.
    """
    return {
        "event": event,
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    }


async def publish_event(event: str, payload: dict[str, Any]) -> bool:
    """Biznes hodisasini `logistika.events` ga yuboradi. Hech qachon istisno tashlamaydi.

    Ataylab "fire-and-forget": hodisa — asosiy amalning yon ta'siri (buyurtma holati
    allaqachon bazaga yozilgan). Broker o'chgani uchun foydalanuvchiga 500 qaytarish
    noto'g'ri bo'lardi — shuning uchun xato faqat logga tushadi va `False` qaytadi.
    Chaqiruvchi natijani tekshirishi shart emas; `False` asosan testlar va
    diagnostika uchun.
    """
    envelope = build_event(event, payload)
    message = aio_pika.Message(
        body=json.dumps(envelope, separators=(",", ":"), default=str).encode(),
        content_type="application/json",
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        message_id=envelope["event_id"],
        type=event,
    )

    try:
        await get_channel()  # `_events_exchange` shu yerda to'ldiriladi
        if _events_exchange is None:
            raise QueueUnavailable("events exchange e'lon qilinmagan")
        await _events_exchange.publish(message, routing_key=event)
        return True
    except Exception:
        logger.exception("Hodisa yuborilmadi: %s (payload=%s)", event, payload)
        return False


async def close_queue() -> None:
    """Ulanishni yopadi (FastAPI shutdown va worker to'xtashida)."""
    global _connection, _channel, _exchange, _events_exchange
    try:
        if _connection is not None and not _connection.is_closed:
            await _connection.close()
    except Exception:
        logger.exception("RabbitMQ ulanishini yopishda xato")
    finally:
        _connection = None
        _channel = None
        _exchange = None
        _events_exchange = None
