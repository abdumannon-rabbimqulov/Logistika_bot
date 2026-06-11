"""
ai/chat_ws.py — Peer chat WebSocket handler (Telegram-like UX).

Event protocol:
  Client → Server: ping | new_message | message_read | typing_start |
                   typing_stop | message_edit | message_delete
  Server → Client: pong | connected | new_message | delivery_update |
                   typing | user_presence | message_edited | message_deleted | error
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import WebSocket, WebSocketDisconnect, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ai import crud, schemas
from ai.models import ChatCategory, Message, MessageStatus
from ai.websocket import manager, verify_websocket_token
from config.config import async_session
from driver import crud as driver_crud
from users import crud as users_crud

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _send(websocket: WebSocket, payload: dict) -> None:
    """Xato bo'lsa log qilib o'tadi, exception ko'tarmaydi."""
    try:
        await websocket.send_json(payload)
    except Exception as exc:
        logger.warning("WS send failed: %s", exc)


def serialize_message(msg) -> dict:
    return schemas.MessageResponse.model_validate(msg).model_dump(mode="json")


async def user_can_access_chat(db: AsyncSession, chat, user_id: int) -> bool:
    if chat.user_id is not None and int(chat.user_id) == int(user_id):
        return True
    if chat.driver_id:
        driver = await driver_crud.get_driver(db, int(chat.driver_id))
        return bool(driver and driver.user_id is not None and int(driver.user_id) == int(user_id))
    return False


async def resolve_sender_type(db: AsyncSession, user_id: int) -> schemas.SenderType:
    driver = await driver_crud.get_driver_by_user_id(db, user_id)
    return schemas.SenderType.DRIVER if driver else schemas.SenderType.USER


# ─── Event handlers ───────────────────────────────────────────────────────────

async def _handle_new_message(
    websocket: WebSocket,
    chat_id: int,
    user_id: int,
    data: dict,
) -> None:
    content = (data.get("content") or "").strip()
    if not content:
        await _send(websocket, {"event": "error", "message": "Bo'sh xabar yuborib bo'lmaydi"})
        return

    reply_to_id = data.get("reply_to_id")
    client_uuid = data.get("uuid")

    async with async_session() as db:
        sender_type = await resolve_sender_type(db, user_id)
        msg = await crud.create_message(
            db,
            schemas.MessageCreate(
                chat_id=chat_id,
                sender_id=user_id,
                sender_type=sender_type,
                content=content,
                status=schemas.MessageStatus.SENT,
                reply_to_id=reply_to_id,
                client_uuid=client_uuid,
            ),
        )

    msg_payload = serialize_message(msg)

    # Xabar saqlandi — sender ga tasdiq (single tick ✓)
    await _send(websocket, {"event": "new_message", "data": msg_payload})

    # Chatdagi boshqalarga yuborish
    delivered_to = await manager.broadcast(
        {"event": "new_message", "data": msg_payload},
        chat_id,
        exclude_user=user_id,
    )

    # Agar peer online bo'lsa → DELIVERED (double tick ✓✓ grey)
    if delivered_to:
        async with async_session() as db:
            await crud.update_message_status(db, msg.id, "delivered")
        await _send(websocket, {
            "event": "delivery_update",
            "data": {"message_id": msg.id, "status": "delivered"},
        })


async def _handle_message_read(
    websocket: WebSocket,
    chat_id: int,
    user_id: int,
    message_ids: list[int],
) -> None:
    if not message_ids:
        return

    async with async_session() as db:
        await crud.handle_message_reads(db, chat_id, user_id, message_ids)

    # Original senderlarga READ bildirishnoma (double tick ✓✓ blue)
    await manager.broadcast(
        {
            "event": "delivery_update",
            "data": {"message_ids": message_ids, "status": "read"},
        },
        chat_id,
        exclude_user=user_id,
    )


async def _handle_message_edit(
    websocket: WebSocket,
    chat_id: int,
    user_id: int,
    data: dict,
) -> None:
    message_id = data.get("message_id")
    new_content = (data.get("content") or "").strip()
    if not message_id or not new_content:
        await _send(websocket, {"event": "error", "message": "message_id va content kerak"})
        return

    async with async_session() as db:
        msg = await crud.get_message(db, message_id)
        if not msg:
            await _send(websocket, {"event": "error", "message": "Xabar topilmadi"})
            return
        if msg.sender_id != user_id:
            await _send(websocket, {"event": "error", "message": "Faqat o'z xabaringizni tahrirlash mumkin"})
            return
        if msg.is_deleted:
            await _send(websocket, {"event": "error", "message": "O'chirilgan xabarni tahrirlash mumkin emas"})
            return

        updated = await crud.update_message(db, message_id, schemas.MessageUpdate(content=new_content))

    await manager.broadcast(
        {"event": "message_edited", "data": serialize_message(updated)},
        chat_id,
    )


async def _handle_message_delete(
    websocket: WebSocket,
    chat_id: int,
    user_id: int,
    data: dict,
) -> None:
    message_id = data.get("message_id")
    if not message_id:
        await _send(websocket, {"event": "error", "message": "message_id kerak"})
        return

    async with async_session() as db:
        msg = await crud.get_message(db, message_id)
        if not msg:
            await _send(websocket, {"event": "error", "message": "Xabar topilmadi"})
            return
        if msg.sender_id != user_id:
            await _send(websocket, {"event": "error", "message": "Faqat o'z xabaringizni o'chirish mumkin"})
            return

        await crud.soft_delete_message(db, message_id)

    await manager.broadcast(
        {"event": "message_deleted", "data": {"message_id": message_id}},
        chat_id,
    )


# ─── Main WebSocket handler ────────────────────────────────────────────────────

async def websocket_peer_chat(websocket: WebSocket, chat_id: int) -> None:
    """Peer-to-peer chat WebSocket handler (Telegram-like events)."""
    token = websocket.query_params.get("token")
    user_id = verify_websocket_token(token)
    if user_id is None:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or missing authentication token",
        )
        return

    # ── Validation phase ───────────────────────────────────────────
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

        # Load recent messages + presence info
        recent = await crud.list_chat_messages(db, chat_id, limit=50)
        peer_last_seen = await crud.get_peer_last_seen(db, chat_id, exclude_user_id=user_id)
        online_peers = [uid for uid in manager.online_users(chat_id) if uid != user_id]

    # ── Connect ────────────────────────────────────────────────────
    await manager.connect(websocket, chat_id, user_id)
    logger.info("WS peer chat connected: user=%s chat=%s", user_id, chat_id)

    # Ulanish holatini peer ga e'lon qilish
    await manager.broadcast(
        {"event": "user_presence", "data": {"user_id": user_id, "online": True}},
        chat_id,
        exclude_user=user_id,
    )

    # Dastlabki snapshot yuborish
    await _send(websocket, {
        "event": "connected",
        "data": {
            "chat_id": chat_id,
            "user_id": user_id,
            "messages": [serialize_message(m) for m in recent],
            "online_peers": online_peers,
            "peer_last_seen": peer_last_seen.isoformat() if peer_last_seen else None,
        },
    })

    # ── Event loop ─────────────────────────────────────────────────
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await _send(websocket, {"event": "pong"})

            elif msg_type == "new_message":
                await _handle_new_message(websocket, chat_id, user_id, data)

            elif msg_type == "message_read":
                ids = data.get("message_ids", [])
                await _handle_message_read(websocket, chat_id, user_id, ids)

            elif msg_type == "typing_start":
                await manager.broadcast(
                    {"event": "typing", "data": {"user_id": user_id, "is_typing": True}},
                    chat_id,
                    exclude_user=user_id,
                )

            elif msg_type == "typing_stop":
                await manager.broadcast(
                    {"event": "typing", "data": {"user_id": user_id, "is_typing": False}},
                    chat_id,
                    exclude_user=user_id,
                )

            elif msg_type == "message_edit":
                await _handle_message_edit(websocket, chat_id, user_id, data)

            elif msg_type == "message_delete":
                await _handle_message_delete(websocket, chat_id, user_id, data)

            else:
                await _send(websocket, {"event": "error", "message": f"Noma'lum tip: {msg_type}"})

    except WebSocketDisconnect:
        manager.disconnect(chat_id, user_id)
        logger.info("WS disconnected: user=%s chat=%s", user_id, chat_id)

        # Peer ga offline bildirishnoma
        await manager.broadcast(
            {
                "event": "user_presence",
                "data": {
                    "user_id": user_id,
                    "online": False,
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                },
            },
            chat_id,
        )

        # DB ga oxirgi ko'rinish vaqtini saqlash
        async with async_session() as db:
            await crud.upsert_presence(db, user_id, chat_id, online=False)

    except Exception as exc:
        logger.error("WS error chat=%s user=%s: %s", chat_id, user_id, exc, exc_info=True)
        await _send(websocket, {"event": "error", "message": "Server xatosi"})
        manager.disconnect(chat_id, user_id)
