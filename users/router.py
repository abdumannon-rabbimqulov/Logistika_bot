from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from config.config import BOT_TOKEN

from users.crud import (
    get_user_by_id,
    get_user_by_phone,
    get_user_by_username,
    update_user,update_password,deactivate_user
)
from users.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_token,
    verify_password,
)
from config.config import get_db
from users.models import User
from users.telegram_auth import validate_telegram_init_data
from users.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    TelegramWebAppLoginRequest,
    Token,
    UserRead,
    UserUpdate,
)

router = APIRouter()




@router.post(
    "/login",
    response_model=Token,
    summary="Login — JWT token olish",
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
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh token orqali yangi tokenlar olish",
)
async def refresh_tokens(
    data: RefreshTokenRequest,
):
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



@router.get(
    "/me",
    response_model=UserRead,
    summary="O'z profilini ko'rish",
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user



@router.patch(
    "/me",
    response_model=UserRead,
    summary="Profilni tahrirlash (full_name, username, phone, language)",
)
async def update_my_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.username and data.username != current_user.username:
        existing = await get_user_by_username(db, data.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu username allaqachon band.",
            )

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
    if not verify_password(data.old_password, current_user.password):
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