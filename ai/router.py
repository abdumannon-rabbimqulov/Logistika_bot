import asyncio
import base64
import logging
import os
import shutil
import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from Admin_panel.validation import is_admin
from ai import agent, crud, schemas
from ai.limits import (
    check_request_quota,
    get_usage_stats,
    increment_usage,
    set_user_limit as set_user_limit_setting,
    set_user_tariff as set_user_tariff_setting,
)
from ai.settings import get_current_model, set_current_model
from ai.websocket import manager
from config.config import (
    AVAILABLE_AI_MODELS,
    MAX_VOICE_MB,
    STATIC_PATH,
    UPLOAD_DIR,
    async_session,
    get_db,
)
from driver import crud as driver_crud
from users import crud as users_crud
from users.auth import get_current_user
from users.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["Logistika AI & Chat"])


# ════════════════════════════════════════════════
# WEBSOCKET — Real-vaqtda muloqot va AI Agent
# ════════════════════════════════════════════════


@router.get("/ws-info", tags=["Documentation"])
async def websocket_info():
    """AI Agent va Chat uchun WebSocket qo'llanmasi."""
    return {
        "url": "ws://domain/api/ai/ws/{chat_id}?token=YOUR_ACCESS_TOKEN",
        "authentication": "JWT access tokenni query parameter sifatida yuboring",
        "events_sent_by_user": [
            {"type": "new_message", "content": "matn", "sender_id": 123},
            {
                "type": "voice_message",
                "audio_b64": "<base64>",
                "mime_type": "audio/webm | audio/ogg | audio/mpeg",
                "sender_id": 123,
            },
        ],
        "events_received": [
            {"event": "new_message", "data": {"...": "Message obyekti"}},
            {"event": "voice_transcribed", "data": {"transcript": "...", "message_id": 1}},
            {"event": "ai_action", "action": "Bajarilmoqda: ..."},
            {
                "event": "ai_limit_exceeded",
                "message": "Kunlik limit tugagan",
                "used": 50,
                "limit": 50,
            },
            {"event": "error", "message": "..."},
        ],
        "error_codes": {"1008": "Invalid token / no access"},
    }


async def _send(websocket: WebSocket, payload: dict) -> None:
    try:
        await websocket.send_json(payload)
    except Exception as exc:
        logger.warning("WS send failed: %s", exc)


async def _run_ai_flow(
    db: AsyncSession,
    websocket: WebSocket,
    chat_id: int,
    user: User,
    log_agent: agent.LogistikaAgent,
    transcript: str,
    is_ai_chat: bool,
    on_action_callback,
) -> None:
    """Quota check + AI process + Message yaratish + broadcast."""
    if not (is_ai_chat or transcript.lower().startswith("ai")):
        return

    allowed, used, limit = await check_request_quota(db, user)
    if not allowed:
        await _send(
            websocket,
            {
                "event": "ai_limit_exceeded",
                "message": f"Kunlik {limit} so'rov limiti tugagan.",
                "used": used,
                "limit": limit,
            },
        )
        return

    try:
        ai_text, usage = await asyncio.wait_for(
            log_agent.process_message(
                transcript, chat_id=chat_id, on_action_callback=on_action_callback
            ),
            timeout=60,
        )
    except asyncio.TimeoutError:
        await _send(websocket, {"event": "error", "message": "AI javob bermadi (timeout)"})
        return

    await increment_usage(
        db,
        user.id,
        requests=1,
        input_tokens=usage.get("input", 0),
        output_tokens=usage.get("output", 0),
    )

    async with async_session() as db2:
        ai_msg = await crud.create_message(
            db2,
            schemas.MessageCreate(
                chat_id=chat_id,
                sender_id=0,
                sender_type=schemas.SenderType.AI,
                content=ai_text,
            ),
        )
        await manager.broadcast(
            {
                "event": "new_message",
                "data": schemas.MessageResponse.model_validate(ai_msg).model_dump(mode="json"),
            },
            chat_id,
        )


@router.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int):
    """AI Agent + Chat WebSocket. Tokendan user_id, role, language olinadi."""
    from ai.websocket import verify_websocket_token

    token = websocket.query_params.get("token")
    user_id = verify_websocket_token(token)
    if user_id is None:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or missing authentication token",
        )
        return

    # ── Connection-level cache (User, Chat) ─────────────────
    async with async_session() as db:
        user = await users_crud.get_user_by_id(db, user_id)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="User not found")
            return

        chat_obj = await crud.get_chat(db, chat_id)
        if not chat_obj:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Chat not found")
            return

        allowed = chat_obj.user_id == user_id
        if not allowed and chat_obj.driver_id:
            driver = await driver_crud.get_driver(db, chat_obj.driver_id)
            allowed = bool(driver and driver.user_id == user_id)
        if not allowed:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Access denied")
            return

        user_lang = user.language or "uz"
        user_role = user.role.value if user.role else "guest"
        is_ai_chat = chat_obj.category == schemas.ChatCategory.AI_COMMAND

    await manager.connect(websocket, chat_id, user_id)
    logger.info(
        "WebSocket connected: user=%s role=%s lang=%s chat=%s",
        user_id, user_role, user_lang, chat_id,
    )

    log_agent = agent.LogistikaAgent(user_id=user_id, role=user_role, language=user_lang)

    async def ai_action_callback(action_text: str):
        await manager.broadcast({"event": "ai_action", "action": action_text}, chat_id)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            # ── Matnli xabar ──────────────────────────────
            if msg_type == "new_message":
                content = (data.get("content") or "").strip()
                if not content:
                    await _send(websocket, {"event": "error", "message": "Bo'sh xabar"})
                    continue

                async with async_session() as db:
                    user_msg = await crud.create_message(
                        db,
                        schemas.MessageCreate(
                            chat_id=chat_id,
                            sender_id=data.get("sender_id", user_id),
                            sender_type=schemas.SenderType.USER,
                            content=content,
                        ),
                    )
                    await manager.broadcast(
                        {
                            "event": "new_message",
                            "data": schemas.MessageResponse.model_validate(user_msg).model_dump(
                                mode="json"
                            ),
                        },
                        chat_id,
                    )

                async with async_session() as db:
                    fresh_user = await users_crud.get_user_by_id(db, user_id) or user
                    await _run_ai_flow(
                        db,
                        websocket,
                        chat_id,
                        fresh_user,
                        log_agent,
                        content,
                        is_ai_chat,
                        ai_action_callback,
                    )

            # ── Ovozli xabar ──────────────────────────────
            elif msg_type == "voice_message":
                audio_b64 = data.get("audio_b64")
                mime_type = data.get("mime_type", "audio/webm")
                if not audio_b64:
                    await _send(websocket, {"event": "error", "message": "audio_b64 yo'q"})
                    continue
                if not mime_type.startswith("audio/"):
                    await _send(
                        websocket,
                        {"event": "error", "message": f"Noto'g'ri mime: {mime_type}"},
                    )
                    continue

                try:
                    audio_bytes = base64.b64decode(audio_b64)
                except Exception:
                    await _send(websocket, {"event": "error", "message": "Audio dekod xato"})
                    continue

                if len(audio_bytes) > MAX_VOICE_MB * 1024 * 1024:
                    await _send(
                        websocket,
                        {
                            "event": "error",
                            "message": f"Audio juda katta (>{MAX_VOICE_MB}MB)",
                        },
                    )
                    continue

                # Quota check (voice ham 1 ta request)
                async with async_session() as db:
                    fresh_user = await users_crud.get_user_by_id(db, user_id) or user
                    allowed, used, limit = await check_request_quota(db, fresh_user)
                if not allowed:
                    await _send(
                        websocket,
                        {
                            "event": "ai_limit_exceeded",
                            "message": f"Kunlik {limit} so'rov limiti tugagan.",
                            "used": used,
                            "limit": limit,
                        },
                    )
                    continue

                # Faylga yozamiz
                ext = mime_type.split("/")[-1].split(";")[0] or "bin"
                fname = f"{uuid.uuid4()}.{ext}"
                fpath = os.path.join(UPLOAD_DIR, fname)
                try:
                    with open(fpath, "wb") as f:
                        f.write(audio_bytes)
                except Exception as exc:
                    logger.error("Audio save failed: %s", exc)
                    await _send(websocket, {"event": "error", "message": "Faylni saqlab bo'lmadi"})
                    continue
                file_url = f"{STATIC_PATH}/{fname}"

                # STT
                await ai_action_callback("Ovoz matnga aylantirilmoqda...")
                try:
                    transcript = await asyncio.wait_for(
                        log_agent.transcribe_audio(audio_bytes, mime_type),
                        timeout=30,
                    )
                except asyncio.TimeoutError:
                    await _send(websocket, {"event": "error", "message": "STT timeout"})
                    continue
                except Exception as exc:
                    logger.error("STT failed: %s", exc)
                    await _send(websocket, {"event": "error", "message": f"STT xatosi: {exc}"})
                    continue

                if not transcript:
                    await _send(
                        websocket,
                        {"event": "error", "message": "Ovoz matnga aylantirib bo'lmadi"},
                    )
                    continue

                # Message + Attachment yaratish
                async with async_session() as db:
                    user_msg = await crud.create_message(
                        db,
                        schemas.MessageCreate(
                            chat_id=chat_id,
                            sender_id=data.get("sender_id", user_id),
                            sender_type=schemas.SenderType.USER,
                            message_type=schemas.MessageType.VOICE,
                            content=transcript,
                            attachments=[
                                schemas.AttachmentCreate(
                                    file_type=schemas.AttachmentType.VOICE,
                                    file_url=file_url,
                                    mime_type=mime_type,
                                    file_size=len(audio_bytes),
                                    transcript=transcript,
                                    transcript_lang=user_lang,
                                )
                            ],
                        ),
                    )

                await manager.broadcast(
                    {
                        "event": "voice_transcribed",
                        "data": {
                            "message_id": user_msg.id,
                            "transcript": transcript,
                            "transcript_lang": user_lang,
                            "file_url": file_url,
                        },
                    },
                    chat_id,
                )

                # AI oqimi (transcript matn sifatida)
                async with async_session() as db:
                    fresh_user = await users_crud.get_user_by_id(db, user_id) or user
                    await _run_ai_flow(
                        db,
                        websocket,
                        chat_id,
                        fresh_user,
                        log_agent,
                        transcript,
                        is_ai_chat,
                        ai_action_callback,
                    )

            else:
                await _send(websocket, {"event": "error", "message": f"Noma'lum tip: {msg_type}"})

    except WebSocketDisconnect:
        manager.disconnect(chat_id, user_id)
        logger.info("WebSocket disconnected: user=%s chat=%s", user_id, chat_id)
    except Exception as exc:
        logger.error("WebSocket error chat=%s: %s", chat_id, exc, exc_info=True)
        manager.disconnect(chat_id, user_id)


# ════════════════════════════════════════════════
# REST endpoints — Chat
# ════════════════════════════════════════════════


@router.post("/chats", response_model=schemas.ChatResponse, summary="Yangi chat yaratish")
async def create_new_chat(
    data: schemas.ChatBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_data = schemas.ChatCreate(user_id=current_user.id, **data.model_dump())
    return await crud.create_chat(db, chat_data)


@router.get("/chats", response_model=List[schemas.ChatResponse], summary="Mening chatlarim")
async def list_my_chats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.list_user_chats(db, current_user.id)


@router.get("/chats/{chat_id}", response_model=schemas.ChatResponse, summary="Chat tafsilotlari")
async def get_chat_details(
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = await crud.get_chat(db, chat_id)
    if not chat or chat.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat topilmadi yoki sizga tegishli emas")
    return chat


@router.patch(
    "/messages/{message_id}",
    response_model=schemas.MessageResponse,
    summary="Xabarni tahrirlash",
)
async def edit_message(
    message_id: int,
    data: schemas.MessageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    msg = await crud.get_message(db, message_id)
    if not msg or msg.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Ruxsat berilmagan")
    updated_msg = await crud.update_message(db, message_id, data)
    await manager.broadcast(
        {
            "event": "message_edited",
            "data": schemas.MessageResponse.model_validate(updated_msg).model_dump(mode="json"),
        },
        msg.chat_id,
    )
    return updated_msg


@router.delete(
    "/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xabarni o'chirish",
)
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    msg = await crud.get_message(db, message_id)
    if not msg or msg.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Ruxsat berilmagan")
    chat_id = msg.chat_id
    await crud.delete_message(db, message_id)
    await manager.broadcast({"event": "message_deleted", "message_id": message_id}, chat_id)
    return None


@router.post("/upload", response_model=dict, summary="Media yuklash")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"url": f"{STATIC_PATH}/{unique_filename}", "filename": file.filename}


@router.post("/ratings", response_model=schemas.RatingResponse, summary="Baho berish")
async def submit_rating(
    data: schemas.RatingBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rating_data = schemas.RatingCreate(
        rated_by_user=current_user.id
        if data.target_type == schemas.RatingTarget.DRIVER
        else None,
        rated_by_driver=current_user.id
        if data.target_type == schemas.RatingTarget.USER
        else None,
        **data.model_dump(),
    )
    return await crud.create_rating(db, rating_data)


# ════════════════════════════════════════════════
# REST endpoints — Limit / usage (foydalanuvchi)
# ════════════════════════════════════════════════


@router.get("/me/usage", summary="Mening bugungi AI sarflarim")
async def my_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allowed, used, limit = await check_request_quota(db, current_user)
    return {
        "allowed": allowed,
        "used_today": used,
        "daily_limit": limit,
    }


# ════════════════════════════════════════════════
# ADMIN endpoints — model va statistika
# ════════════════════════════════════════════════


@router.get("/admin/models", summary="Mavjud AI model'lar (admin)")
async def admin_list_models(admin: User = Depends(is_admin)):
    current = await get_current_model()
    return schemas.CurrentModelResponse(model_name=current, available=AVAILABLE_AI_MODELS)


@router.get("/admin/model", summary="Joriy AI model (admin)")
async def admin_get_model(admin: User = Depends(is_admin)):
    current = await get_current_model()
    return schemas.CurrentModelResponse(model_name=current, available=AVAILABLE_AI_MODELS)


@router.post("/admin/model", summary="AI model'ni almashtirish (admin)")
async def admin_set_model(
    payload: schemas.SetModelRequest,
    admin: User = Depends(is_admin),
):
    if payload.model_name not in AVAILABLE_AI_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{payload.model_name}' ruxsat etilgan ro'yxatda emas: {AVAILABLE_AI_MODELS}",
        )
    await set_current_model(payload.model_name)
    return {"model_name": payload.model_name, "status": "updated"}


@router.patch(
    "/admin/users/{user_id}/limit",
    summary="Foydalanuvchi kunlik AI limitini sozlash (admin)",
)
async def admin_set_user_limit(
    user_id: int,
    payload: schemas.SetUserLimitRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(is_admin),
):
    user = await users_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User topilmadi")
    await set_user_limit_setting(db, user_id, payload.daily_requests)
    return {"user_id": user_id, "daily_requests": payload.daily_requests}


@router.patch(
    "/admin/users/{user_id}/tariff",
    summary="Foydalanuvchi tarifini sozlash (admin)",
)
async def admin_set_user_tariff(
    user_id: int,
    payload: schemas.SetUserTariffRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(is_admin),
):
    user = await users_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User topilmadi")
    tariff = await set_user_tariff_setting(db, user_id, payload.tariff)
    return {"user_id": user_id, "tariff": tariff}


@router.get(
    "/admin/usage",
    response_model=schemas.UsageStatsResponse,
    summary="Barcha foydalanuvchilar AI sarflari (admin)",
)
async def admin_get_usage(
    user_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[date] = Query(None, description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(is_admin),
):
    rows = await get_usage_stats(db, user_id=user_id, date_from=date_from, date_to=date_to)

    items = [schemas.UsageStatRow.model_validate(r) for r in rows]
    return schemas.UsageStatsResponse(
        items=items,
        total_requests=sum(r.requests for r in rows),
        total_input_tokens=sum(r.input_tokens for r in rows),
        total_output_tokens=sum(r.output_tokens for r in rows),
    )
