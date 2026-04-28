import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import BOT_TOKEN, EOTP_EXPIRE_SECONDS, get_db
from users.crud import (
    create_otp,
    create_user_by_email,
    deactivate_user,
    get_active_otp,
    get_user_by_email,
    get_user_by_id,
    get_user_by_phone,
    get_user_by_username,
    mark_otp_used,
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
from users.email_service import generate_otp, send_otp_email
from users.models import User, UserRole
from users.telegram_auth import validate_telegram_init_data
from users.schemas import (
    ChangePasswordRequest,
    DriverProfileRequest,
    EmailLoginRequest,
    EmailRegisterRequest,
    EmailVerifyRequest,
    LoginRequest,
    RefreshTokenRequest,
    SelectRoleRequest,
    TelegramWebAppLoginRequest,
    Token,
    TokenWithStep,
    UserRead,
    UserUpdate,
)
from driver.crud import create_driver, get_driver_by_user_id

logger = logging.getLogger(__name__)
router = APIRouter()


# ───────────────────────────────────────────────────────────────────────────
# 1-QADAM: RO'YXATDAN O'TISH — Email ga OTP yuborish
# POST /register
# ───────────────────────────────────────────────────────────────────────────

@router.post(
    "/register",
    status_code=status.HTTP_200_OK,
    summary="Ro'yxatdan o'tish (1-qadam: OTP yuborish)",
    description="""
    Foydalanuvchi email, parol va to'liq ism yuboradi.
    Server 6 xonali tasdiqlash kodini email ga jo'natadi.
    Keyingi qadam: **POST /verify-email**
    """,
)
async def register_by_email(
    data: EmailRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # Email allaqachon ro'yxatdan o'tganmi?
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu email allaqachon ro'yxatdan o'tgan. Login sahifasiga o'ting.",
        )

    # OTP yaratish va DB ga saqlash
    otp_code  = generate_otp()
    hashed_pw = hash_password(data.password)

    await create_otp(
        db,
        email=data.email,
        code=otp_code,
        hashed_pw=hashed_pw,
        full_name=data.full_name,
        language=data.language or "uz",
        expire_seconds=EOTP_EXPIRE_SECONDS,
    )

    # Email yuborish
    try:
        await send_otp_email(
            to_email=data.email,
            otp_code=otp_code,
            full_name=data.full_name,
        )
        logger.info("OTP yuborildi: %s", data.email)
    except Exception as exc:
        logger.error("Email yuborishda xato: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Email yuborishda xato yuz berdi. SMTP sozlamalarini tekshiring.",
        )

    return {
        "detail": f"Tasdiqlash kodi {data.email} manziliga yuborildi.",
        "expires_in_seconds": EOTP_EXPIRE_SECONDS,
        "next_step": "verify-email",
    }


# ───────────────────────────────────────────────────────────────────────────
# 2-QADAM: OTP TASDIQLASH — Akkaunt yaratish
# POST /verify-email
# ───────────────────────────────────────────────────────────────────────────

@router.post(
    "/verify-email",
    response_model=TokenWithStep,
    summary="OTP tasdiqlash (2-qadam: Akkaunt yaratish)",
    description="""
    Email va OTP kodni yuborasiz.
    Muvaffaqiyatli bo'lsa akkaunt yaratiladi va JWT token qaytariladi.
    **next_step = "select_role"** — keyingi qadam rolni tanlash.
    """,
)
async def verify_email_otp(
    data: EmailVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    # DB dan aktiv OTP ni topish
    otp = await get_active_otp(db, data.email)
    if otp is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu email uchun aktiv OTP topilmadi. "
                   "Avval /register ga murojaat qiling yoki muddati tugagan.",
        )

    # Kod tekshiruvi
    if data.code != otp.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP kod noto'g'ri. Qaytadan tekshiring.",
        )

    # OTP ni ishlatilgan deb belgilash
    await mark_otp_used(db, otp)

    # User yaratish
    user = await create_user_by_email(
        db,
        full_name=otp.full_name,
        email=data.email,
        hashed_password=otp.hashed_pw,
        language=otp.language,
    )
    logger.info("Yangi user yaratildi: id=%s email=%s", user.id, data.email)

    payload = {"sub": str(user.id)}
    return TokenWithStep(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        next_step="select_role",
        message="Akkaunt muvaffaqiyatli yaratildi! Endi rolingizni tanlang.",
    )


# ───────────────────────────────────────────────────────────────────────────
# 3-QADAM: ROL TANLASH
# POST /select-role
# ───────────────────────────────────────────────────────────────────────────

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
    # Faqat GUEST rolidagi user rol tanlashi mumkin
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


# ───────────────────────────────────────────────────────────────────────────
# 4-QADAM: DRIVER PROFILI TO'LDIRISH
# POST /driver-profile
# ───────────────────────────────────────────────────────────────────────────

@router.post(
    "/driver-profile",
    response_model=TokenWithStep,
    summary="Driver profili (4-qadam, faqat driver uchun)",
    description="""
    Haydovchi o'z yuk mashinasi haqida ma'lumot kiritadi.
    Truck type ID ni **GET /api/drivers/truck-types** dan olishingiz mumkin.
    """,
)
async def fill_driver_profile(
    data: DriverProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Faqat driver roli bo'lganda ruxsat
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu endpoint faqat haydovchilar uchun. Avval /select-role orqali 'driver' tanlang.",
        )

    # Driver profili allaqachon bor?
    existing_driver = await get_driver_by_user_id(db, current_user.id)
    if existing_driver:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Haydovchi profili allaqachon to'ldirilgan.",
        )

    # Truck number band emasmi?
    from sqlalchemy import select as sa_select
    from driver.models import Driver as DriverModel
    truck_check = await db.execute(
        sa_select(DriverModel).where(DriverModel.truck_number == data.truck_number)
    )
    if truck_check.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"'{data.truck_number}' davlat raqami allaqachon ro'yxatdan o'tgan.",
        )

    # Driver yaratish
    await create_driver(
        db,
        user_id=current_user.id,
        truck_type_id=data.truck_type_id,
        truck_number=data.truck_number,
        current_city=data.current_city,
        truck_brand=data.truck_brand,
        truck_year=data.truck_year,
        capacity_ton=data.capacity_ton,
        capacity_m3=data.capacity_m3,
    )

    # Telefon raqam bo'lsa user ga ham saqlash
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


# ───────────────────────────────────────────────────────────────────────────
# EMAIL ORQALI LOGIN
# POST /login-email
# ───────────────────────────────────────────────────────────────────────────

@router.post(
    "/login-email",
    response_model=TokenWithStep,
    summary="Email va parol orqali tizimga kirish",
)
async def login_by_email(
    data: EmailLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_email(db, data.email)
    if user is None or not verify_password(data.password, user.password or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email yoki parol noto'g'ri.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Akkaunt bloklangan.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akkaunt faol emas.")

    payload    = {"sub": str(user.id)}
    # Role asosida next_step aniqlash
    if user.role == UserRole.GUEST:
        next_step = "select_role"
        message   = "Iltimos, rolingizni tanlang."
    elif user.role == UserRole.DRIVER:
        driver = await get_driver_by_user_id(db, user.id)
        if driver is None:
            next_step = "fill_driver_profile"
            message   = "Haydovchi profilingizni to'ldiring."
        else:
            next_step = "done"
            message   = "Xush kelibsiz!"
    else:
        next_step = "done"
        message   = "Xush kelibsiz!"

    return TokenWithStep(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload),
        next_step=next_step,
        message=message,
    )


# ───────────────────────────────────────────────────────────────────────────
# TELEFON RAQAM ORQALI LOGIN (eski usul)
# POST /login
# ───────────────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=Token,
    summary="Telefon + parol orqali login",
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user: User | None = None

    if data.phone_number:
        user = await get_user_by_phone(db, data.phone_number)

    if user is None or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Akkaunt bloklangan.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akkaunt faol emas.")

    payload = {"sub": str(user.id)}
    access_token  = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    return Token(access_token=access_token, refresh_token=refresh_token)


# ───────────────────────────────────────────────────────────────────────────
# TOKEN YANGILASH
# POST /refresh
# ───────────────────────────────────────────────────────────────────────────

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


# ───────────────────────────────────────────────────────────────────────────
# TELEGRAM WEBAPP LOGIN
# POST /telegram/webapp-login
# ───────────────────────────────────────────────────────────────────────────

@router.post(
    "/telegram/webapp-login",
    response_model=Token,
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
    return Token(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
    )


# ───────────────────────────────────────────────────────────────────────────
# O'Z PROFILINI KO'RISH / TAHRIRLASH
# ───────────────────────────────────────────────────────────────────────────

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