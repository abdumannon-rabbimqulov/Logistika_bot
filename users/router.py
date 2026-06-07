import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import BOT_TOKEN, get_db, REDIS_HOST, REDIS_PORT, REDIS_DB
from handlers.verification_code import send_verification_code
from users.crud import (

    deactivate_user,
    get_user_by_id,
    get_user_by_phone,
    update_password,
    update_user,
)
from users.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
    verify_token,
)
from users.models import User, UserRole, VerificationCode
from users.telegram_auth import validate_telegram_init_data
from users.schemas import (
    ChangePasswordRequest,
    RefreshTokenRequest,
    Token,
    UserRead,
    UserUpdate,
)
from driver.crud import  get_driver_by_user_id
from utils.validation import normalize_phone_number

import redis
from datetime import timedelta, datetime, timezone

from handlers.bot import bot

redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
)

logger = logging.getLogger(__name__)
router = APIRouter()



@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh token orqali yangi tokenlar olish",
)
async def refresh_tokens(data: RefreshTokenRequest):

    payload = verify_token(data.refresh_token)

    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token yaroqsiz yoki muddati tugagan.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Refresh token xato")

    saved_token=redis_client.get(f"blacklist_refresh_{data.refresh_token}")
    if saved_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bu refresh token allaqachon ishlatilgan yoki yaroqsiz.",
        )

    token_payload = {"sub": str(user_id)}
    return Token(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
    )



@router.post("/login", summary="")
async def login(
    phone_number: Optional[str] = Body(None, embed=True),
    password: Optional[str] = Body(None, embed=True),
    init_data: Optional[str] = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
):
    user = None

    if phone_number:
        try:
            phone_number = normalize_phone_number(phone_number)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    if init_data:
        if not BOT_TOKEN:
            raise HTTPException(status_code=500, detail="BOT_TOKEN sozlanmagan")

        try:
            tg_user = validate_telegram_init_data(init_data, BOT_TOKEN)
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

        tg_user_id = tg_user.get("id")
        if not tg_user_id:
            raise HTTPException(status_code=400, detail="Telegram user id topilmadi")

        user = await get_user_by_id(db, int(tg_user_id))

        if user is None:
            user = User(
                id=int(tg_user_id),
                username=tg_user.get("username"),
                full_name=" ".join(
                    p for p in [tg_user.get("first_name"), tg_user.get("last_name")] if p
                ) or "Telegram User",
                language="uz",
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

    else:
        if not phone_number or not password:
            raise HTTPException(
                status_code=400,
                detail="init_data yoki phone_number va password yuborilishi kerak.",
            )

        user = await get_user_by_phone(db, phone_number)

        if not user or not user.password or not verify_password(password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Telefon raqam yoki parol noto'g'ri.",
            )

    if user.role == UserRole.DRIVER:
        existing_driver = await get_driver_by_user_id(db, user.id)
        if not existing_driver:
            return {
                "access_token": create_access_token({"sub": str(user.id)}),
                "refresh_token": create_refresh_token({"sub": str(user.id)}),
                "role": user.role,
                "user_id": user.id,
                "status": "need_driver_profile",
                "message": "Haydovchi rolini tanlagansiz, lekin profil ma'lumotlaringiz to'liq emas.",
            }

    token_payload = {"sub": str(user.id)}

    return {
        "access_token": create_access_token(token_payload),
        "refresh_token": create_refresh_token(token_payload),
        "role": user.role,
        "user_id": user.id,
    }


@router.post(
    "/reset-phone",
    summary="Telefon raqam bor bolsa code yuboriladi",)
async def reset_phone(
    phone_number: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    try:
        phone_number = normalize_phone_number(phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    user = await get_user_by_phone(db, phone_number)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bunday telefon raqam bilan foydalanuvchi topilmadi.",
        )
    if not user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foydalanuvchining Telegram akkaunti ulanmagan.",
        )
    code = await send_verification_code(
        bot=bot,
        telegram_id=user.id,
    )
    verification_code = VerificationCode(
        user_id=user.id,
        code=code,
    )
    db.add(verification_code)
    await db.commit()

    token_payload = {"sub": str(user.id)}
    return {"detail": "Tasdiqlash kodi Telegram akkauntingizga yuborildi.",
            "access_token": create_access_token(token_payload),
            }

@router.post(
    "/verify-reset-code",
    summary="Tasdiqlash kodini tekshirish va parolni tiklash",
)
async def verify_reset_code(
    current_user: User = Depends(get_current_user),
    code: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
):
    user=current_user
    if not user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foydalanuvchining Telegram akkaunti ulanmagan.",
        )
    verification_code = await db.execute(
        select(VerificationCode).where(
            VerificationCode.user_id == user.id,
            VerificationCode.code == code,
            VerificationCode.expires_at > datetime.now(timezone.utc),
        )
    )
    verification_code = verification_code.scalars().first()
    if not verification_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tasdiqlash kodi noto'g'ri yoki muddati tugagan.",
        )
    await db.delete(verification_code)
    await db.commit()
    return {"detail": "Kod tasdiqlandi. Endi yangi parolni tiklash uchun /reset-password endpoint'iga murojaat qilishingiz mumkin."}



@router.post(
    "/reset-password",
    summary="Parolni tiklash (telefon raqam orqali)",
)
async def reset_password(
    current_user: User = Depends(get_current_user),
    new_password: str = Body(..., embed=True,min_length=8,max_length=20),
    confirm_password: str = Body(..., embed=True,min_length=8,max_length=20),
    db: AsyncSession = Depends(get_db),
):
    user=current_user
    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yangi parol va tasdiqlash paroli mos kelmadi.",
        )

    new_hashed_password = hash_password(new_password)
    await update_password(db, user, new_hashed_password)
    return {"detail": "Parol muvaffaqiyatli tiklandi."}


@router.get(
    "/me",
    response_model=UserRead,
    summary="O'z profilini ko'rish",
)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Profilni tahrirlash",
)
async def update_my_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.phone_number and data.phone_number != current_user.phone_number:
        existing = await get_user_by_phone(db, data.phone_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu telefon raqam allaqachon ro'yxatdan o'tgan.",
            )
    return await update_user(db, current_user, data)


@router.patch(
    "/me/password",
    status_code=status.HTTP_200_OK,
    summary="Parolni o'zgartirish",
)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.old_password, current_user.password or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Eski parol noto'g'ri.",
        )
    new_hash = hash_password(data.new_password)
    await update_password(db, current_user, new_hash)
    return {"detail": "Parol muvaffaqiyatli o'zgartirildi."}


@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Akkauntni o'chirish (deactivate)",
)
async def delete_my_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await deactivate_user(db, current_user)
    return {"detail": "Akkaunt muvaffaqiyatli deaktivatsiya qilindi."}


@router.post("/logout")
async def logout(
    data: Optional[RefreshTokenRequest] = Body(None),
    refresh_token_query: Optional[str] = Query(None, alias="refresh_token"),
    current_user: User = Depends(get_current_user),
):
    refresh_token = data.refresh_token if data else refresh_token_query
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token talab qilinadi")

    payload = verify_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token yaroqsiz yoki muddati tugagan.",
        )
    user_id = payload.get("sub")
    if not user_id or str(user_id) != str(current_user.id):
        raise HTTPException(status_code=401, detail="Refresh token xato")
    try:
        redis_client.set(f"blacklist_refresh_{refresh_token}", "true", ex=timedelta(days=1))
    except (redis.exceptions.RedisError, OSError) as exc:
        logger.warning("Redis logout blacklist unavailable, local logout only: %s", exc)
    return {"detail": "Muvaffaqiyatli logout qilindi."}
