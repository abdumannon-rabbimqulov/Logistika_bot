import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import BOT_TOKEN, get_db
from users.crud import (

    deactivate_user,
    get_user_by_id,
    get_user_by_phone,
    update_password,
    update_user,
    update_user_role,
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
    SelectRoleRequest,
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

logger = logging.getLogger(__name__)
router = APIRouter()








@router.post(
    "/select-role",
    response_model=TokenWithStep,
    summary="Rol tanlash (3-qadam): driver yoki sender",
    description="""
    Foydalanuvchi kim ekanini bildiradi: **driver** yoki **sender**.

    - **sender** → next_step = "done" (barcha bosqichlar tugaydi)
    - **driver** → next_step = "fill_driver_profile" (mashina ma'lumotlari kerak)
    """,
)
async def select_role(
    data: SelectRoleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in (UserRole.GUEST,):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Siz allaqachon '{current_user.role.value}' roliga egasiz.",
        )

    new_role = UserRole.DRIVER if data.role == "driver" else UserRole.SENDER
    await update_user_role(db, current_user, new_role)

    payload = {"sub": str(current_user.id)}

    if new_role == UserRole.DRIVER:
        return TokenWithStep(
            access_token=create_access_token(payload),
            refresh_token=create_refresh_token(payload),
            next_step="fill_driver_profile",
            message="Rol saqlandi! Endi yuk mashina ma'lumotlarini kiriting.",
        )
    else:
        return TokenWithStep(
            access_token=create_access_token(payload),
            refresh_token=create_refresh_token(payload),
            next_step="done",
            message="Ro'yxatdan o'tish muvaffaqiyatli yakunlandi! Xush kelibsiz.",
        )



@router.post(
    "/driver-profile",
    response_model=TokenWithStep,
    summary="Driver profili (4-qadam, faqat driver uchun)",
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
        capacity_ton=data.capacity_ton,
        capacity_m3=data.capacity_m3,
        current_city=data.current_city,
        is_active=True
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

    token_payload = {"sub": str(user.id)}
    return {
        "access_token": create_access_token(token_payload),
        "refresh_token": create_refresh_token(token_payload),
        "role": user.role,
        "user_id": user.id
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