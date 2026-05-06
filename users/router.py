import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import BOT_TOKEN, get_db, REDIS_HOST, REDIS_PORT, REDIS_DB
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
from users.models import User, UserRole
from users.telegram_auth import validate_telegram_init_data
from users.schemas import (
    ChangePasswordRequest,
    RefreshTokenRequest,
    TelegramWebAppLoginRequest,
    Token,
    TokenWithStep,
    UserRead,
    UserUpdate,
)
from driver.crud import  get_driver_by_user_id
from sqlalchemy import select as sa_select
from driver.models import Driver as DriverModel
from driver.schemas import DriverCreate

import redis
from datetime import timedelta

redis_client = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
)

logger = logging.getLogger(__name__)
router = APIRouter()



@router.post(
    "/driver-profile",
    response_model=TokenWithStep,
    summary="Driver profili to'ldirish (faqat haydovchilar uchun",
)
async def fill_driver_profile(
    data: DriverCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu endpoint faqat haydovchilar uchun. Avval /select-role orqali 'driver' tanlang.",
        )

    existing_driver = await get_driver_by_user_id(db, current_user.id)
    if existing_driver:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Haydovchi profili allaqachon to'ldirilgan.",
        )



    truck_check = await db.execute(
        sa_select(DriverModel).where(DriverModel.truck_number == data.truck_number)
    )
    if truck_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{data.truck_number}' davlat raqami allaqachon ro'yxatdan o'tgan.",
        )

    new_driver = DriverModel(
        user_id=current_user.id,
        truck_type_id=data.truck_type_id,
        truck_number=data.truck_number,
        truck_year=data.truck_year,
        current_city=data.current_city,
        current_region=data.current_region,
    )
    db.add(new_driver)

    if data.phone_number:
        current_user.phone_number = data.phone_number

    await db.commit()

    logger.info("Driver profili yaratildi: user_id=%s truck=%s", current_user.id, data.truck_number)

    payload = {"sub": str(current_user.id)}
    return TokenWithStep(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        next_step="done",
        message="Profil muvaffaqiyatli to'ldirildi! Xush kelibsiz, haydovchi.",
    )




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



@router.post(
    "/login",
    summary="Telegram WebApp initData orqali login",
)
async def telegram_webapp_login(
    data: TelegramWebAppLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="BOT_TOKEN sozlanmagan")

    try:
        tg_user = validate_telegram_init_data(data.init_data, BOT_TOKEN)
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

    if user.role==UserRole.DRIVER:
        existing_driver = await get_driver_by_user_id(db, user.id)
        if not existing_driver:
            logger.info("Telegram foydalanuvchisi haydovchi rolini tanlagan, lekin profil to'ldirilmagan: user_id=%s", user.id)
            return {
                "access_token": create_access_token({"sub": str(user.id)}),
                "refresh_token": create_refresh_token({"sub": str(user.id)}),
                "role": user.role,
                "user_id": user.id,
                "status": "need_driver_profile",
                "message": "Haydovchi rolini tanlagansiz, lekin profil ma'lumotlaringiz to'liq emas. Iltimos, /driver-profile endpoint orqali profil ma'lumotlaringizni to'ldiring.",
            }

    token_payload = {"sub": str(user.id)}
    return {
        "access_token": create_access_token(token_payload),
        "refresh_token": create_refresh_token(token_payload),
        "role": user.role,
        "user_id": user.id,
    }


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
    if data.old_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yangi parol eski paroldan farq qilishi kerak.",
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
async def logout(refresh_token: str, current_user: User = Depends(get_current_user)):
    payload = verify_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token yaroqsiz yoki muddati tugagan.",
        )
    user_id = payload.get("sub")
    if not user_id or str(user_id) != str(current_user.id):
        raise HTTPException(status_code=401, detail="Refresh token xato")
    redis_client.set(f"blacklist_refresh_{refresh_token}", "true", ex=timedelta(days=1))
    return {"detail": "Muvaffaqiyatli logout qilindi."}
