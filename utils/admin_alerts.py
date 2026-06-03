

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Iterable
from urllib import error, parse, request

from config.config import ADMIN_IDS, BOT_TOKEN

logger = logging.getLogger(__name__)


def _truncate(text: str, limit: int = 3200) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n... [truncated]"


def _send_sync(chat_id: int, text: str) -> None:
    """Telegram Bot API'ga POST /sendMessage (sync)."""
    if not BOT_TOKEN:
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


async def send_error_to_admins(
    *,
    title: str,
    request_id: str,
    method: str,
    path: str,
    client: str,
    exc_type: str,
    details: str,
    admin_ids: Iterable[int] | None = None,
) -> None:
    """Xatoni adminlarga yuboradi. Hech qachon exception tashlamaydi."""
    ids = list(admin_ids if admin_ids is not None else ADMIN_IDS)
    if not ids:
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    message = (
        f"🚨 Backend Error Alert\n"
        f"{title}\n\n"
        f"time: {now}\n"
        f"request_id: {request_id}\n"
        f"method: {method}\n"
        f"path: {path}\n"
        f"client: {client}\n"
        f"exc_type: {exc_type}\n\n"
        f"details:\n{details}"
    )
    message = _truncate(message, 3500)

    for admin_id in ids:
        try:
            await asyncio.to_thread(_send_sync, int(admin_id), message)
        except (ValueError, error.URLError, error.HTTPError, TimeoutError) as exc:
            logger.warning("Admin alert send failed for %s: %s", admin_id, exc)
        except Exception as exc:
            logger.warning("Unexpected admin alert error for %s: %s", admin_id, exc)


def format_details_for_alert(exc: Exception, *, max_len: int = 1200) -> str:
    raw = f"{type(exc).__name__}: {exc}"
    if len(raw) <= max_len:
        return raw
    return raw[: max_len - 20] + "... [truncated]"

