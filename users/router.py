from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

import crud
from auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from config.config import get_db
from models import User
from schemas import (
    ChangePasswordRequest,
    LoginRequest,
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
        user = await crud.get_user_by_phone(db, data.phone_number)

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

    token = create_access_token(user_id=user.id)
    return Token(access_token=token)



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
    # username yoki phone boshqa foydalanuvchiga tegishli emasligini tekshirish
    if data.username and data.username != current_user.username:
        existing = await crud.get_user_by_username(db, data.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu username allaqachon band.",
            )

    if data.phone_number and data.phone_number != current_user.phone_number:
        existing = await crud.get_user_by_phone(db, data.phone_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu telefon raqam allaqachon ro'yxatdan o'tgan.",
            )

    return await crud.update_user(db, current_user, data)


# ──────────────────────────────────────────────
#  PAROL O'ZGARTIRISH  →  PATCH /auth/me/password
# ──────────────────────────────────────────────

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
    await crud.update_password(db, current_user, new_hash)
    return {"detail": "Parol muvaffaqiyatli o'zgartirildi."}


# ──────────────────────────────────────────────
#  PROFILNI O'CHIRISH  →  DELETE /auth/me
# ──────────────────────────────────────────────

@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    summary="Akkauntni o'chirish (deactivate)",
)
async def delete_my_account(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Foydalanuvchi akkauntini to'liq o'chirish o'rniga
    is_active = False qilib qo'yamiz (xavfsizroq).
    """
    await crud.deactivate_user(db, current_user)
    return {"detail": "Akkaunt muvaffaqiyatli deaktivatsiya qilindi."}