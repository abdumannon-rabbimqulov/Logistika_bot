"""Support (Yordam) mikroservizi — mustaqil FastAPI ilovasi.

Ishga tushirish:  `uvicorn support_service.main:app --host 0.0.0.0 --port 8000`
(docker-compose'dagi `support` xizmati aynan shuni bajaradi, tashqi port 8010.)

Chegara: bu xizmat asosiy loyihaning kodini ham, bazasini ham ishlatmaydi. Uni
asosiy tizim bilan bog'lab turadigan yagona narsa — umumiy `SECRET_KEY` (JWT
tekshirish uchun) va RabbitMQ dagi `logistika.events` exchange'i.

Hodisa iste'molchisi shu jarayonning ichida, `lifespan` da `consume` sifatida
ishlaydi. Lokal sinash uchun konteyner soni kam bo'lsin degan qaror: yuk ortganda
uni alohida konteynerga ajratish uchun `_consume_events` ni `python -m` bilan
ishga tushadigan alohida faylga ko'chirish kifoya (`workers/events_worker.py` naqshi).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from support_service import crud, queue
from support_service.config import LOG_LEVEL
from support_service.db import async_session, engine
from support_service.models import Base
from support_service.router import router as support_router

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("support_service")

_STATUS_LABEL = {
    "scheduled": "rejalashtirilgan",
    "pending": "haydovchi qidirilmoqda",
    "accepted": "haydovchi biriktirildi",
    "in_progress": "yo'lda",
    "completed": "yakunlandi",
    "cancelled": "bekor qilindi",
}


async def _handle_order_event(event: str, data: dict[str, Any]) -> None:
    """Buyurtma hodisasini shu buyurtmaga oid ochiq murojaatlarga izoh qilib qo'shadi.

    Foyda: operator murojaatni ochganda buyurtma bilan nima bo'lganini alohida
    tizimga kirmasdan ko'radi — support asosiy bazaga ulanmagani uchun bu ma'lumot
    boshqa yo'l bilan kelmasdi.
    """
    order_id = data.get("order_id")
    if not order_id:
        return

    if event == queue.EVENT_ORDER_STATUS_CHANGED:
        new_status = str(data.get("new_status", ""))
        old_status = str(data.get("old_status", ""))
        body = (
            f"Buyurtma #{order_id} holati o'zgardi: "
            f"{_STATUS_LABEL.get(old_status, old_status)} → "
            f"{_STATUS_LABEL.get(new_status, new_status)}"
        )
        actor = data.get("changed_by_role")
        if actor:
            body += f" ({actor})"
    elif event == queue.EVENT_ORDER_TRUCK_ASSIGNED:
        body = (
            f"Buyurtma #{order_id} ga yuk mashinasi biriktirildi: "
            f"{data.get('truck_number')} (haydovchi id={data.get('driver_id')})"
        )
    else:
        return

    async with async_session() as db:
        tickets = await crud.list_open_tickets_for_order(db, int(order_id))
        for ticket in tickets:
            await crud.add_message(db, ticket, body, is_system=True)
        if tickets:
            logger.info(
                "%s: %s ta murojaatga tizim izohi qo'shildi (order #%s)",
                event,
                len(tickets),
                order_id,
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Sxema startda yaratiladi (asosiy ilovadagi kabi) — bu mikroserviz uchun
    # alohida alembic zanjiri ortiqcha murakkablik bo'lardi.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    consumer_tag = None
    try:
        consumer_tag = await queue.consume_order_events(_handle_order_event)
    except queue.QueueUnavailable:
        # Broker hali ko'tarilmagan bo'lsa ham API ishlayversin: murojaat yaratish
        # RabbitMQ'ga bog'liq emas, faqat bildirishnoma kechikadi.
        logger.warning("RabbitMQ hozircha mavjud emas — hodisalar tinglanmayapti")

    yield

    if consumer_tag is not None:
        try:
            channel = await queue.get_channel()
            events_queue = await channel.get_queue(queue.SUPPORT_EVENTS_QUEUE)
            await events_queue.cancel(consumer_tag)
        except Exception:
            logger.exception("Consumer'ni to'xtatishda xato")
    await queue.close_queue()
    await engine.dispose()


app = FastAPI(
    title="Logistika Support Service",
    version="1.0.0",
    description="Yordam (Support) mikroservizi — murojaatlar va yozishmalar",
    lifespan=lifespan,
)

app.include_router(support_router)


@app.get("/health", tags=["Service"], summary="Sog'liq tekshiruvi")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "support"}
