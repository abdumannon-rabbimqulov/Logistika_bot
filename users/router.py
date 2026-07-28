import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import (
    BOT_TOKEN,
    get_db,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from handlers.verification_code import send_verification_code
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
    create_password_reset_token,
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
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordSchema,
    ResetPhoneSchema,
    RoleSelectRequest,
    Token,
    UserRead,
    UserUpdate,
    VerifyResetCodeSchema,
)
from driver.crud import  get_driver_by_user_id
from utils.validation import normalize_phone_number

import redis.asyncio as aioredis
from redis import exceptions as redis_exceptions
from datetime import timedelta, datetime, timezone

from handlers.bot import bot

# Async Redis — event loop bloklanmasligi uchun sinxron `redis.Redis` emas.
redis_client = aioredis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Brute-force / spam himoyasi uchun sozlamalar
LOGIN_MAX_ATTEMPTS = 10          # bitta telefon+IP uchun oynadagi maksimal urinish
LOGIN_WINDOW_SEC = 300           # 5 daqiqa
RESET_CODE_COOLDOWN_SEC = 60     # kod qayta yuborish uchun kutish vaqti


async def _rate_limit_ok(key: str, max_hits: int, window_sec: int) -> bool:
    """Redis INCR asosidagi oddiy, jarayonlararo umumiy rate limiter.

    Redis ishlamasa — xizmatni to'smaslik uchun ruxsat beradi (fail-open).
    """
    try:
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, window_sec)
        return current <= max_hits
    except (redis_exceptions.RedisError, OSError) as exc:
        logger.warning("Rate limit tekshiruvi uchun Redis mavjud emas: %s", exc)
        return True



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

    blacklist_key = f"blacklist_refresh_{data.refresh_token}"
    try:
        saved_token = await redis_client.get(blacklist_key)
    except (redis_exceptions.RedisError, OSError) as exc:
        logger.error("Refresh blacklist tekshiruvi uchun Redis mavjud emas: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vaqtincha xizmat mavjud emas, keyinroq urinib ko'ring.",
        ) from exc

    if saved_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bu refresh token allaqachon ishlatilgan yoki yaroqsiz.",
        )

    # Rotatsiya: eski refresh token endi ishlatib bo'linmaydi (bir martalik).
    try:
        await redis_client.set(blacklist_key, "1", ex=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    except (redis_exceptions.RedisError, OSError) as exc:
        logger.error("Refresh token rotatsiyasi saqlanmadi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vaqtincha xizmat mavjud emas, keyinroq urinib ko'ring.",
        ) from exc

    token_payload = {"sub": str(user_id)}
    return Token(
        access_token=create_access_token(token_payload),
        refresh_token=create_refresh_token(token_payload),
    )



@router.post("/login", summary="Telefon+parol yoki Telegram initData orqali kirish")
async def login(
    request: Request,
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user = None
    phone_number = data.phone_number
    password = data.password
    init_data = data.init_data

    if phone_number:
        try:
            phone_number = normalize_phone_number(phone_number)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # Brute-force himoyasi: parol orqali kirishda telefon+IP bo'yicha cheklov.
    if phone_number and password:
        client_ip = request.client.host if request.client else "unknown"
        rl_key = f"login_attempts:{phone_number}:{client_ip}"
        if not await _rate_limit_ok(rl_key, LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SEC):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Juda ko'p urinish. Bir necha daqiqadan so'ng qayta urinib ko'ring.",
            )

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

    # Banlangan yoki nofaol akkauntga token berilmaydi.
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akkaunt bloklangan.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akkaunt faol emas.",
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
    summary="Parolni tiklash uchun Telegramga tasdiqlash kodi yuboradi",
)
async def reset_phone(
    data: ResetPhoneSchema,
    db: AsyncSession = Depends(get_db),
):
    """1-qadam: telefon raqam bo'yicha Telegramga kod yuborish.

    So'rov `application/json` body ko'rinishida qabul qilinadi (`/auth/login` kabi).

    Xavfsizlik: bu endpoint HECH QANDAY token qaytarmaydi. Foydalanuvchi
    mavjudligini oshkor qilmaslik uchun har doim bir xil javob beriladi
    (user enumeration'ni oldini olish).
    """
    try:
        phone_number = normalize_phone_number(data.phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    generic_response = {
        "detail": "Agar bu raqam ro'yxatdan o'tgan bo'lsa, Telegram akkauntingizga tasdiqlash kodi yuborildi.",
    }

    user = await get_user_by_phone(db, phone_number)
    if not user or not user.id:
        return generic_response

    # Kodni tez-tez qayta yuborishni cheklash (spam / SMS-bomba himoyasi).
    cooldown_key = f"reset_cooldown:{user.id}"
    if not await _rate_limit_ok(cooldown_key, 1, RESET_CODE_COOLDOWN_SEC):
        return generic_response

    code = await send_verification_code(bot=bot, telegram_id=user.id)
    db.add(VerificationCode(user_id=user.id, code=code))
    await db.commit()
    return generic_response


@router.post(
    "/verify-reset-code",
    summary="Tasdiqlash kodini tekshirish (parol tiklash tokenini beradi)",
)
async def verify_reset_code(
    data: VerifyResetCodeSchema,
    db: AsyncSession = Depends(get_db),
):
    """2-qadam: kod to'g'ri bo'lsa, faqat parol tiklash uchun qisqa muddatli
    token qaytariladi. Bu token boshqa endpointlar uchun yaroqsiz."""
    code = data.code
    try:
        phone_number = normalize_phone_number(data.phone_number)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    user = await get_user_by_phone(db, phone_number)
    invalid_exc = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tasdiqlash kodi noto'g'ri yoki muddati tugagan.",
    )
    if not user or not user.id:
        raise invalid_exc

    result = await db.execute(
        select(VerificationCode).where(
            VerificationCode.user_id == user.id,
            VerificationCode.code == code,
            VerificationCode.expires_at > datetime.now(timezone.utc),
        )
    )
    verification_code = result.scalars().first()
    if not verification_code:
        raise invalid_exc

    # Kod bir martalik — tasdiqlangach o'chiriladi.
    await db.delete(verification_code)
    await db.commit()

    return {
        "detail": "Kod tasdiqlandi. Endi /reset-password ga reset_token bilan murojaat qiling.",
        "reset_token": create_password_reset_token({"sub": str(user.id)}),
    }


@router.post(
    "/reset-password",
    summary="Parolni tiklash (verify-reset-code bergan reset_token bilan)",
)
async def reset_password(
    data: ResetPasswordSchema,
    db: AsyncSession = Depends(get_db),
):
    """3-qadam: reset_token tekshiriladi va yangi parol o'rnatiladi."""
    new_password = data.new_password
    confirm_password = data.confirm_password
    payload = verify_token(data.reset_token)
    if not payload or payload.get("type") != "reset":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Parol tiklash tokeni yaroqsiz yoki muddati tugagan.",
        )

    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yangi parol va tasdiqlash paroli mos kelmadi.",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token xato")

    user = await get_user_by_id(db, int(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi.",
        )

    await update_password(db, user, hash_password(new_password))
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


@router.post(
    "/select-role",
    response_model=UserRead,
    summary="Ro'yxatdan o'tishda rolni birinchi marta tanlash (GUEST -> sender/driver)",
)
async def select_role(
    data: RoleSelectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Faqat hali rol tanlanmagan (GUEST) foydalanuvchi o'zi tanlay oladi — sender/driver
    # bo'lib bo'lgan (yoki admin/dispatcher/manager) foydalanuvchi bu orqali o'zgartira
    # olmaydi (buni faqat admin panel qila oladi).
    if current_user.role != UserRole.GUEST:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rolingiz allaqachon belgilangan.",
        )
    new_role = UserRole.SENDER if data.role == "sender" else UserRole.DRIVER
    return await update_user_role(db, current_user, new_role)


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
        await redis_client.set(
            f"blacklist_refresh_{refresh_token}",
            "true",
            ex=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        )
    except (redis_exceptions.RedisError, OSError) as exc:
        logger.warning("Redis logout blacklist unavailable, local logout only: %s", exc)
    return {"detail": "Muvaffaqiyatli logout qilindi."}
