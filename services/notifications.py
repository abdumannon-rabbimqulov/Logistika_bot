"""Telegram orqali foydalanuvchilarga xabar yuborish (FastAPI + bot API)."""

from __future__ import annotations

import asyncio
import logging
from typing import Iterable, Literal

DeletedBy = Literal["admin", "sender"]
from urllib import error, parse, request

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import BOT_TOKEN
from driver.models import Driver

logger = logging.getLogger(__name__)


def _truncate(text: str, limit: int = 3200) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n... [truncated]"


def _send_sync(chat_id: int, text: str) -> None:
    """Telegram Bot API POST /sendMessage (sync, thread-safe)."""
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN yo'q — Telegram xabari yuborilmadi (chat_id=%s)", chat_id)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(chat_id),
        "text": _truncate(text),
        "disable_web_page_preview": "true",
    }
    data = parse.urlencode(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with request.urlopen(req, timeout=6) as resp:  # noqa: S310
        _ = resp.read()


async def send_telegram_message(chat_id: int, text: str) -> None:
    """Bitta Telegram chat_id ga xabar; xato bo'lsa exception tashlamaydi."""
    try:
        await asyncio.to_thread(_send_sync, int(chat_id), text)
    except (ValueError, error.URLError, error.HTTPError, TimeoutError) as exc:
        logger.warning("Telegram xabar yuborilmadi (chat_id=%s): %s", chat_id, exc)
    except Exception as exc:
        logger.warning("Kutilmagan Telegram xato (chat_id=%s): %s", chat_id, exc)


def order_deleted_message(cargo_name: str, deleted_by: DeletedBy) -> str:
    if deleted_by == "sender":
        return (
            f"Siz taklif bergan '{cargo_name}' buyurtmasi "
            f"mijoz tomonidan bekor qilindi (o'chirildi)."
        )
    return (
        f"Siz taklif bergan '{cargo_name}' buyurtmasi admin tomonidan o'chirildi."
    )


async def notify_drivers_order_deleted(
    db: AsyncSession,
    driver_ids: Iterable[int],
    cargo_name: str,
    *,
    deleted_by: DeletedBy = "admin",
) -> None:
    """Buyurtmaga taklif bergan haydovchilarga (Telegram user_id) xabar yuboradi."""
    unique_driver_ids = {int(d) for d in driver_ids}
    if not unique_driver_ids:
        return

    message = order_deleted_message(cargo_name, deleted_by)

    result = await db.execute(
        select(Driver.user_id).where(Driver.id.in_(unique_driver_ids))
    )
    chat_ids = {int(uid) for uid in result.scalars().all() if uid is not None}

    for chat_id in chat_ids:
        await send_telegram_message(chat_id, message)
