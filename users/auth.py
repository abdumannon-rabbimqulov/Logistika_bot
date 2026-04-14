from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from users.crud import get_user_by_id
from config.config import (get_db,
        SECRET_KEY,ALGORITHM,pwd_context,
        ACCESS_TOKEN_EXPIRE_MINUTES
        )



def hash_password(plain: str) -> str:
    """Ochiq parolni bcrypt bilan hash qiladi."""
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Parolni tekshiradi."""
    return pwd_context.verify(plain, hashed)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

class TokenData(BaseModel):
    user_id: int

def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise ValueError
        return TokenData(user_id=int(user_id))
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz yoki muddati o'tgan.",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):


    token_data = decode_token(token)
    user = await get_user_by_id(db, token_data.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Akkaunt bloklangan.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Akkaunt faol emas.")
    return user

