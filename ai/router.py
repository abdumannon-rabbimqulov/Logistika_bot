import logging
import os
import shutil
import uuid
import aiofiles
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
from ai.assistant import ask_assistant
from ai.limits import (
    check_request_quota,
    get_usage_stats,
    set_user_limit as set_user_limit_setting,
    set_user_tariff as set_user_tariff_setting,
)
from ai.settings import get_current_model, set_current_model

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
