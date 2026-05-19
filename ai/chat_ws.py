"""WebSocket — faqat foydalanuvchilar o'rtasida matnli chat (AI emas)."""

from __future__ import annotations

import logging

from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai import crud, schemas
from ai.models import ChatCategory
from ai.websocket import manager, verify_websocket_token
from config.config import async_session
from driver import crud as driver_crud
from users import crud as users_crud
logger = logging.getLogger(__name__)


async def _send(websocket: WebSocket, payload: dict) -> None:
    try:
        await websocket.send_json(payload)
    except Exception as exc:
        logger.warning("WS send failed: %s", exc)


def message_payload(msg) -> dict:
    return schemas.MessageResponse.model_validate(msg).model_dump(mode="json")


async def user_can_access_chat(db: AsyncSession, chat, user_id: int) -> bool:
    if chat.user_id == user_id:
        return True
    if chat.driver_id:
        driver = await driver_crud.get_driver(db, chat.driver_id)
        return bool(driver and driver.user_id == user_id)
    return False


async def resolve_sender_type(db: AsyncSession, user_id: int) -> schemas.SenderType:
    driver = await driver_crud.get_driver_by_user_id(db, user_id)
    if driver:
        return schemas.SenderType.DRIVER
    return schemas.SenderType.USER


async def websocket_peer_chat(websocket: WebSocket, chat_id: int) -> None:
    token = websocket.query_params.get("token")
    user_id = verify_websocket_token(token)
    if user_id is None:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or missing authentication token",
        )
        return

    async with async_session() as db:
        user = await users_crud.get_user_by_id(db, user_id)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            return

        chat_obj = await crud.get_chat(db, chat_id)
        if not chat_obj:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Chat not found")
            return

        if chat_obj.category == ChatCategory.AI_COMMAND:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="AI chat uses REST POST /ai/assistant/message",
            )
            return

        if not await user_can_access_chat(db, chat_obj, user_id):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Access denied")
            return

        sender_type = await resolve_sender_type(db, user_id)
        await crud.mark_messages_as_read(db, chat_id)
        recent = await crud.list_chat_messages(db, chat_id, limit=40)

    await manager.connect(websocket, chat_id, user_id)
    logger.info("WS peer chat: user=%s chat=%s", user_id, chat_id)

    await _send(
        websocket,
        {
            "event": "connected",
            "data": {
                "chat_id": chat_id,
                "user_id": user_id,
                "messages": [message_payload(m) for m in recent],
            },
        },
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await _send(websocket, {"event": "pong"})
                continue

            if msg_type == "new_message":
                content = (data.get("content") or "").strip()
                if not content:
                    await _send(websocket, {"event": "error", "message": "Bo'sh xabar"})
                    continue

                async with async_session() as db:
                    st = await resolve_sender_type(db, user_id)
                    user_msg = await crud.create_message(
                        db,
                        schemas.MessageCreate(
                            chat_id=chat_id,
                            sender_id=user_id,
                            sender_type=st,
                            content=content,
                        ),
                    )
                await manager.broadcast(
                    {"event": "new_message", "data": message_payload(user_msg)},
                    chat_id,
                )
                continue

            await _send(websocket, {"event": "error", "message": f"Noma'lum tip: {msg_type}"})

    except WebSocketDisconnect:
        manager.disconnect(chat_id, user_id)
        logger.info("WS disconnected: user=%s chat=%s", user_id, chat_id)
    except Exception as exc:
        logger.error("WS error chat=%s: %s", chat_id, exc, exc_info=True)
        await _send(websocket, {"event": "error", "message": str(exc)})
        manager.disconnect(chat_id, user_id)
