
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai import agent, crud, schemas
from ai.limits import check_request_quota, increment_usage
from ai.models import ChatCategory
from users.models import User

logger = logging.getLogger(__name__)


@dataclass
class AssistantResult:
    reply: str
    chat_id: int
    used_today: int
    daily_limit: int
    allowed: bool


async def _resolve_ai_chat(db: AsyncSession, user: User, chat_id: Optional[int]):
    if chat_id is None:
        return await crud.get_or_create_ai_chat(db, user.id)

    chat = await crud.get_chat(db, chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat topilmadi")
    if chat.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ruxsat berilmagan")
    if chat.category != ChatCategory.AI_COMMAND:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu chat AI yordamchi emas. POST /ai/assistant/message faqat ai_command chat uchun.",
        )
    return chat


async def ask_assistant(
    db: AsyncSession,
    user: User,
    message: str,
    *,
    chat_id: Optional[int] = None,
) -> AssistantResult:
    """Matnli savol → matnli javob (WebSocket ishlatilmaydi)."""
    text = (message or "").strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bo'sh xabar")

    allowed, used, limit = await check_request_quota(db, user)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": f"Kunlik {limit} so'rov limiti tugagan.",
                "used_today": used,
                "daily_limit": limit,
            },
        )

    chat = await _resolve_ai_chat(db, user, chat_id)
    chat_id = chat.id

    user_role = user.role.value if user.role else "sender"
    user_lang = user.language or "uz"
    if user_role == "driver":
        log_agent = agent.DriverAgent(user_id=user.id, language=user_lang)
    else:
        log_agent = agent.SenderAgent(user_id=user.id, language=user_lang)

    user_msg = await crud.create_message(
        db,
        schemas.MessageCreate(
            chat_id=chat_id,
            sender_id=user.id,
            sender_type=schemas.SenderType.USER,
            content=text,
        ),
    )

    history = await crud.build_agent_history(
        db, chat_id, exclude_message_id=user_msg.id
    )

    try:
        ai_text, usage = await asyncio.wait_for(
            log_agent.process_message(text, chat_id=chat_id, history=history),
            timeout=90,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI javob bermadi (timeout)",
        )
    except Exception as exc:
        logger.error("ask_assistant error user=%s: %s", user.id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI xatosi: {exc}",
        )

    await increment_usage(
        db,
        user.id,
        requests=1,
        input_tokens=usage.get("input", 0),
        output_tokens=usage.get("output", 0),
    )

    await crud.create_message(
        db,
        schemas.MessageCreate(
            chat_id=chat_id,
            sender_id=None,
            sender_type=schemas.SenderType.AI,
            message_type=schemas.MessageType.AI_REPLY,
            content=ai_text,
            is_ai_response=True,
        ),
    )

    _, used_after, limit_after = await check_request_quota(db, user)
    return AssistantResult(
        reply=ai_text,
        chat_id=chat_id,
        used_today=used_after,
        daily_limit=limit_after,
        allowed=True,
    )
