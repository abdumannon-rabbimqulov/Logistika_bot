import logging
import os
import shutil
import uuid
from datetime import date
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from Admin_panel.validation import is_admin
from ai import crud, schemas
from ai.models import ChatCategory
from ai.assistant import ask_assistant
from ai.chat_ws import user_can_access_chat, websocket_peer_chat
from ai.limits import (
    check_request_quota,
    get_usage_stats,
    set_user_limit as set_user_limit_setting,
    set_user_tariff as set_user_tariff_setting,
)
from ai.settings import get_current_model, set_current_model
from ai.websocket import manager
from config.config import (
    AI_DAILY_LIMIT_FREE,
    AI_DAILY_LIMIT_PRO,
    AVAILABLE_AI_MODELS,
    MODEL_NAME,
    STATIC_PATH,
    UPLOAD_DIR,
    get_db,
)
from users import crud as users_crud
from users.auth import get_current_user
from users.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["Logistika AI & Chat"])


# ════════════════════════════════════════════════
# WEBSOCKET — faqat user ↔ user/driver chat
# ════════════════════════════════════════════════


@router.get("/ws-info", tags=["Documentation"])
async def websocket_info():
    """Peer chat WebSocket qo'llanmasi (AI bu yerda emas)."""
    from config.config import API_PUBLIC_PREFIX

    base = API_PUBLIC_PREFIX or ""
    return {
        "url": f"wss://logistic.org.uz{base}/ai/ws/{{chat_id}}?token=YOUR_ACCESS_TOKEN",
        "note": "AI yordamchi uchun WebSocket emas — POST /ai/assistant/message",
        "ai_assistant": f"POST {base}/ai/assistant/message",
        "events_sent_by_user": [
            {"type": "ping"},
            {"type": "new_message", "content": "matn"},
        ],
        "events_received": [
            {"event": "connected", "data": {"chat_id": 1, "messages": []}},
            {"event": "pong"},
            {"event": "new_message", "data": {"...": "Message"}},
            {"event": "message_edited"},
            {"event": "message_deleted"},
            {"event": "error", "message": "..."},
        ],
        "error_codes": {
            "1008": "Invalid token / no access / AI chat (use REST instead)",
        },
    }


@router.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int):
    """Foydalanuvchilar o'rtasida real-vaqt matnli chat."""
    await websocket_peer_chat(websocket, chat_id)


# ════════════════════════════════════════════════
# REST — AI yordamchi (faqat matn)
# ════════════════════════════════════════════════


@router.post(
    "/assistant/message",
    response_model=schemas.AssistantMessageResponse,
    summary="AI yordamchiga matnli savol",
)
async def assistant_message(
    body: schemas.AssistantMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await ask_assistant(
        db, current_user, body.message, chat_id=body.chat_id
    )
    return schemas.AssistantMessageResponse(
        reply=result.reply,
        chat_id=result.chat_id,
        used_today=result.used_today,
        daily_limit=result.daily_limit,
        allowed=result.allowed,
    )


@router.get(
    "/assistant/chat",
    response_model=schemas.ChatResponse,
    summary="AI yordamchi chatini olish yoki yaratish",
)
async def assistant_get_chat(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.get_or_create_ai_chat(db, current_user.id)


@router.get(
    "/assistant/messages",
    response_model=List[schemas.MessageResponse],
    summary="AI chat xabarlari",
)
async def assistant_list_messages(
    chat_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if chat_id is None:
        chat = await crud.get_or_create_ai_chat(db, current_user.id)
        chat_id = chat.id
    else:
        chat = await crud.get_chat(db, chat_id)
        if not chat or chat.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Chat topilmadi")
        if chat.category != ChatCategory.AI_COMMAND:
            raise HTTPException(status_code=400, detail="Bu AI chat emas")
    return await crud.list_chat_messages(db, chat_id, limit=limit, before_id=before_id)




@router.post("/chats", response_model=schemas.ChatResponse, summary="Yangi chat yaratish")
async def create_new_chat(
    data: schemas.ChatBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_data = schemas.ChatCreate(user_id=current_user.id, **data.model_dump())
    return await crud.create_chat(db, chat_data)


@router.post(
    "/chats/assistant",
    response_model=schemas.ChatResponse,
    summary="AI chat (alias: GET /assistant/chat)",
    deprecated=True,
)
async def get_or_create_assistant_chat_legacy(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await crud.get_or_create_ai_chat(db, current_user.id)


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
    if not chat or not await user_can_access_chat(db, chat, current_user.id):
        raise HTTPException(status_code=404, detail="Chat topilmadi yoki sizga tegishli emas")
    return chat


@router.get(
    "/chats/{chat_id}/messages",
    response_model=List[schemas.MessageResponse],
    summary="Chat xabarlari",
)
async def list_chat_messages(
    chat_id: int,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = await crud.get_chat(db, chat_id)
    if not chat or not await user_can_access_chat(db, chat, current_user.id):
        raise HTTPException(status_code=404, detail="Chat topilmadi yoki sizga tegishli emas")
    return await crud.list_chat_messages(db, chat_id, limit=limit, before_id=before_id)


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
# REST — Limit / usage (foydalanuvchi)
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
# ADMIN — model va statistika
# ════════════════════════════════════════════════


@router.get(
    "/admin/settings",
    response_model=schemas.AdminAISettingsResponse,
    summary="AI sozlamalari (admin)",
)
async def admin_ai_settings(admin: User = Depends(is_admin)):
    current = await get_current_model()
    return schemas.AdminAISettingsResponse(
        current_model=current,
        available_models=AVAILABLE_AI_MODELS,
        free_daily_limit=AI_DAILY_LIMIT_FREE,
        pro_daily_limit=AI_DAILY_LIMIT_PRO,
        default_model_env=MODEL_NAME or "gemini-flash-latest",
    )


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
