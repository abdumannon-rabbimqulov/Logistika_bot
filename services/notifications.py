"""Telegram orqali foydalanuvchilarga xabar yuborish (FastAPI + bot API)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Literal, Optional

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


def inline_keyboard(buttons: list[list[tuple[str, str]]]) -> dict:
    """[[("✅ Qabul qilish", "dispatch:accept:5")], ...] -> Telegram `reply_markup` dict.

    Ikkinchi element "http://"/"https://" bilan boshlansa — havola tugmasi (url),
    aks holda odatdagi callback tugmasi bo'ladi.
    """

    def _button(text: str, action: str) -> dict:
        key = "url" if action.startswith(("http://", "https://")) else "callback_data"
        return {"text": text, key: action}

    return {"inline_keyboard": [[_button(text, action) for text, action in row] for row in buttons]}


def url_keyboard(buttons: list[list[tuple[str, Optional[str]]]]) -> Optional[dict]:
    """inline_keyboard kabi, lekin URL'i None bo'lgan tugmalarni tashlab ketadi.

    Koordinata bo'lmasa navigatsiya havolasi tuzilmaydi (None qaytadi) — shunda
    tugma umuman ko'rsatilmasligi kerak. Hech narsa qolmasa None qaytariladi.
    """
    rows = [[(text, url) for text, url in row if url] for row in buttons]
    non_empty = [row for row in rows if row]
    if not non_empty:
        return None
    return inline_keyboard(non_empty)  # type: ignore[arg-type]


def _send_sync(chat_id: int, text: str, reply_markup: Optional[dict] = None) -> Optional[int]:
    """Telegram Bot API POST /sendMessage (sync, thread-safe). Yuborilgan xabar id'sini qaytaradi."""
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN yo'q — Telegram xabari yuborilmadi (chat_id=%s)", chat_id)
        return None
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": str(chat_id),
        "text": _truncate(text),
        "disable_web_page_preview": "true",
    }
    if reply_markup is not None:
        payload["reply_markup"] = json.dumps(reply_markup)
    data = parse.urlencode(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with request.urlopen(req, timeout=6) as resp:  # noqa: S310
        body = json.loads(resp.read().decode("utf-8"))
    return body.get("result", {}).get("message_id")


def _edit_sync(chat_id: int, message_id: int, text: str, reply_markup: Optional[dict] = None) -> None:
    """Telegram Bot API POST /editMessageText (sync, thread-safe)."""
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": str(chat_id),
        "message_id": str(message_id),
        "text": _truncate(text),
        "disable_web_page_preview": "true",
    }
    # reply_markup berilmasa (None) — tugmalar olib tashlanadi (bo'sh inline_keyboard)
    payload["reply_markup"] = json.dumps(reply_markup if reply_markup is not None else {"inline_keyboard": []})
    data = parse.urlencode(payload).encode("utf-8")
    req = request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    with request.urlopen(req, timeout=6) as resp:  # noqa: S310
        _ = resp.read()


async def send_telegram_message(
    chat_id: int, text: str, *, reply_markup: Optional[dict] = None
) -> Optional[int]:
    """Bitta Telegram chat_id ga xabar; xato bo'lsa exception tashlamaydi. Xabar id qaytaradi."""
    try:
        return await asyncio.to_thread(_send_sync, int(chat_id), text, reply_markup)
    except (ValueError, error.URLError, error.HTTPError, TimeoutError) as exc:
        logger.warning("Telegram xabar yuborilmadi (chat_id=%s): %s", chat_id, exc)
    except Exception as exc:
        logger.warning("Kutilmagan Telegram xato (chat_id=%s): %s", chat_id, exc)
    return None


async def edit_telegram_message(
    chat_id: int, message_id: int, text: str, *, reply_markup: Optional[dict] = None
) -> None:
    """Avval yuborilgan xabarni tahrirlaydi (masalan "⏱ Vaqt tugadi"); xato bo'lsa jim ketadi."""
    if not chat_id or not message_id:
        return
    try:
        await asyncio.to_thread(_edit_sync, int(chat_id), int(message_id), text, reply_markup)
    except (ValueError, error.URLError, error.HTTPError, TimeoutError) as exc:
        logger.warning("Telegram xabar tahrirlanmadi (chat_id=%s, message_id=%s): %s", chat_id, message_id, exc)
    except Exception as exc:
        logger.warning("Kutilmagan Telegram tahrirlash xatosi (chat_id=%s): %s", chat_id, exc)


def order_deleted_message(cargo_name: str, deleted_by: DeletedBy) -> str:
    if deleted_by == "sender":
        return (
            f"Sizga biriktirilgan '{cargo_name}' buyurtmasi "
            f"mijoz tomonidan bekor qilindi (o'chirildi)."
        )
    return (
        f"Sizga biriktirilgan '{cargo_name}' buyurtmasi admin tomonidan o'chirildi."
    )


async def notify_drivers_order_deleted(
    db: AsyncSession,
    driver_id: int,
    cargo_name: str,
    *,
    deleted_by: DeletedBy = "admin",
) -> None:
    """Buyurtmaga biriktirilgan haydovchiga (Telegram user_id) bekor qilingani haqida xabar yuboradi."""
    result = await db.execute(
        select(Driver.user_id).where(Driver.id == int(driver_id))
    )
    chat_id = result.scalar_one_or_none()
    if chat_id is None:
        return

    message = order_deleted_message(cargo_name, deleted_by)
    await send_telegram_message(int(chat_id), message)
