"""RabbitMQ consumer: support mikroservizidan kelgan hodisalarni qayta ishlaydi.

Ishga tushirish:  `python -m workers.events_worker`
(docker-compose'dagi `events-worker` xizmati aynan shuni bajaradi.)

Nima qiladi: `support.notifications` navbatini (`logistika.events` exchange'idagi
`support.*` kalitlari) o'qiydi va yangi murojaat kelganda / javob yozilganda
adminlarga Telegram orqali xabar beradi (`utils/admin_alerts.py`).

Nega alohida jarayon: support mikroservizining o'zi Telegram'ga yoza olmaydi —
unda `BOT_TOKEN` ham, adminlar ro'yxati ham yo'q (u asosiy tizim haqida hech narsa
bilmasligi kerak). U faqat "murojaat yaratildi" deb e'lon qiladi, bildirishnoma
esa asosiy tizimning ishi. Shu bilan ikki xizmat o'rtasida to'g'ridan-to'g'ri
HTTP bog'liqlik ham paydo bo'lmaydi.

Xato bo'lganda xabar `requeue=False` bilan tashlanadi: bildirishnoma — kritik
bo'lmagan yon ta'sir, uni cheksiz qayta urinish navbatni tiqib qo'yishi mumkin.
Xatoning o'zi logda qoladi.
"""

from __future__ import annotations

import asyncio
import json
import logging
import signal
from typing import Any, Optional

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.orm import configure_mappers

# Mapper'lar satr nomlari bilan bog'langan — ishlatishdan oldin BARCHA model moduli
# import qilingan bo'lishi shart (workers/dispatch_worker.py dagi kabi).
import Admin_panel.models  # noqa: F401
import driver.models  # noqa: F401
import order.dispatch_models  # noqa: F401
import order.models  # noqa: F401
import users.models  # noqa: F401

configure_mappers()

from services import queue  # noqa: E402
from services.notifications import send_telegram_message  # noqa: E402
from utils.admin_alerts import send_notice_to_admins  # noqa: E402

logger = logging.getLogger("events_worker")

PREFETCH = 10

_PRIORITY_LABEL = {
    "low": "past",
    "normal": "o'rta",
    "high": "yuqori",
    "urgent": "shoshilinch",
}

# Murojaat holatining foydalanuvchiga ko'rinadigan nomi (support_service/models.py
# `TicketStatus` qiymatlari). Frontenddagi `TICKET_STATUS_LABELS` bilan bir xil.
_TICKET_STATUS_LABEL = {
    "open": "ochiq",
    "in_progress": "ko'rib chiqilmoqda",
    "resolved": "hal qilindi",
    "closed": "yopildi",
}

STAFF_ROLES = {"admin", "manager"}


def _format_ticket_created(data: dict[str, Any]) -> tuple[str, str]:
    order_part = f"Buyurtma: #{data['order_id']}\n" if data.get("order_id") else ""
    priority = _PRIORITY_LABEL.get(str(data.get("priority", "")), data.get("priority", "-"))
    body = (
        f"Murojaat: #{data.get('ticket_id')}\n"
        f"Foydalanuvchi: {data.get('user_id')} ({data.get('user_role') or '-'})\n"
        f"{order_part}"
        f"Muhimlik: {priority}\n"
        f"Mavzu: {data.get('subject')}\n\n"
        f"{(data.get('body') or '')[:500]}"
    )
    return "Yangi yordam murojaati", body


def _format_ticket_replied(data: dict[str, Any]) -> tuple[str, str]:
    body = (
        f"Murojaat: #{data.get('ticket_id')}\n"
        f"Muallif: {data.get('author_user_id')} ({data.get('author_role') or '-'})\n\n"
        f"{(data.get('message') or '')[:500]}"
    )
    return "Yordam murojaatiga yangi javob", body


async def _notify_user(chat_id: Any, text: str) -> None:
    """Murojaat egasiga Telegram xabari. Xato bo'lsa faqat logga yoziladi.

    `users.id` ning o'zi Telegram chat id (`users/models.py`) — support xizmati
    bazasidagi `user_id` ham o'sha, shuning uchun qo'shimcha izlash kerak emas.
    Foydalanuvchi botni bloklagan bo'lishi mumkin: bu butun hodisani muvaffaqiyatsiz
    deb hisoblash uchun sabab emas, adminga xabar baribir borishi kerak.
    """
    if not chat_id:
        return
    try:
        await send_telegram_message(int(chat_id), text)
    except Exception:
        logger.exception("Foydalanuvchiga xabar yuborilmadi (chat_id=%s)", chat_id)


def _user_text_ticket_created(data: dict[str, Any]) -> str:
    return (
        f"✅ Murojaatingiz qabul qilindi — #{data.get('ticket_id')}\n"
        f"Mavzu: {data.get('subject')}\n\n"
        f"Operatorlarimiz tez orada javob beradi. Javob shu yerga va ilovadagi "
        f"\"Murojaatlar\" bo'limiga keladi."
    )


def _user_text_ticket_replied(data: dict[str, Any]) -> str:
    return (
        f"💬 Murojaatingizga javob keldi — #{data.get('ticket_id')}\n\n"
        f"{(data.get('message') or '')[:1500]}\n\n"
        f"Javob yozish uchun ilovadagi \"Murojaatlar\" bo'limini oching."
    )


def _user_text_status_changed(data: dict[str, Any]) -> str:
    new_status = str(data.get("new_status", ""))
    label = _TICKET_STATUS_LABEL.get(new_status, new_status)
    text = (
        f"ℹ️ Murojaat #{data.get('ticket_id')} holati o'zgardi: {label}\n"
        f"Mavzu: {data.get('subject')}"
    )
    if new_status in {"resolved", "closed"}:
        text += "\n\nSavolingiz qolgan bo'lsa, yangi murojaat oching."
    return text


async def _handle_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        try:
            envelope = json.loads(message.body)
            event = str(envelope["event"])
            data = envelope.get("data") or {}
        except (ValueError, KeyError, TypeError):
            logger.exception("Yaroqsiz hodisa tashlab yuborildi: %r", message.body[:200])
            return

        # Har bir hodisa ikki tomonga borishi mumkin: adminlarga (nazorat uchun) va
        # murojaat egasiga (u javobni kutayotgan odam). Ikkalasi mustaqil: biri
        # yuborilmasa ham ikkinchisi ketaveradi.
        title: Optional[str] = None
        body = ""

        if event == queue.EVENT_SUPPORT_TICKET_CREATED:
            title, body = _format_ticket_created(data)
            await _notify_user(data.get("user_id"), _user_text_ticket_created(data))
        elif event == queue.EVENT_SUPPORT_TICKET_REPLIED:
            if str(data.get("author_role")) in STAFF_ROLES:
                # Xodimning javobi — adminlarga qaytarib xabar berishning ma'nosi yo'q,
                # lekin murojaat egasi aynan shuni kutib turibdi.
                await _notify_user(
                    data.get("ticket_user_id"), _user_text_ticket_replied(data)
                )
            else:
                title, body = _format_ticket_replied(data)
        elif event == queue.EVENT_SUPPORT_TICKET_STATUS_CHANGED:
            await _notify_user(data.get("ticket_user_id"), _user_text_status_changed(data))
        else:
            logger.debug("E'tiborsiz hodisa: %s", event)
            return

        if title is None:
            return

        try:
            await send_notice_to_admins(title=title, details=body)
        except Exception:
            logger.exception("Adminlarga bildirishnoma yuborilmadi: %s", event)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    channel = await queue.get_channel()  # topologiyani ham e'lon qiladi
    await channel.set_qos(prefetch_count=PREFETCH)
    events_queue = await channel.get_queue(queue.SUPPORT_NOTIFICATIONS_QUEUE)

    consumer_tag: Optional[str] = await events_queue.consume(_handle_message)
    logger.info(
        "Events worker ishga tushdi: '%s' navbati, prefetch=%s",
        queue.SUPPORT_NOTIFICATIONS_QUEUE,
        PREFETCH,
    )

    try:
        await stop.wait()
    finally:
        logger.info("To'xtatilmoqda…")
        try:
            await events_queue.cancel(consumer_tag)
        except Exception:
            logger.exception("Consumer'ni to'xtatishda xato")
        await asyncio.sleep(1)
        await queue.close_queue()
        logger.info("Events worker to'xtadi")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
