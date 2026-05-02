from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


# ═══════════════════════════════════════════════════════════════════════════
# TOKEN
# ═══════════════════════════════════════════════════════════════════════════

class Token(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"


class TokenWithStep(Token):
    """
    Token + keyingi qadam yo'riqnomasi.
    next_step qiymatlari:
      "select_role"        → foydalanuvchi rolini tanlashi kerak
      "fill_driver_profile" → driver profili to'ldirilishi kerak
      "done"               → barcha bosqichlar tugadi
    """
    next_step: Literal["select_role", "fill_driver_profile", "done"]
    message:   Optional[str] = None



# ═══════════════════════════════════════════════════════════════════════════
# ROL TANLASH — 3-qadam
# ═══════════════════════════════════════════════════════════════════════════

class SelectRoleRequest(BaseModel):
    """
    Foydalanuvchi kim ekanini bildiradi.
    role: "driver" yoki "sender"
    """
    role: Literal["driver", "sender"] = Field(..., description="'driver' yoki 'sender'")



# ═══════════════════════════════════════════════════════════════════════════
# USER READ / UPDATE
# ═══════════════════════════════════════════════════════════════════════════

class UserRead(BaseModel):
    id:           int
    username:     Optional[str]
    full_name:    str
    email:        Optional[str]
    phone_number: Optional[str]
    role:         Optional[str]
    language:     str
    is_active:    bool
    is_banned:    bool
    balance:      Decimal
    created_at:   datetime
    updated_at:   datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name:    Optional[str] = Field(None, max_length=128)
    phone_number: Optional[str] = Field(None, max_length=20)
    language:     Optional[str] = Field(None, min_length=2, max_length=10)
    bio:          Optional[str] = Field(None, max_length=500)


# ═══════════════════════════════════════════════════════════════════════════
# BOSHQA
# ═══════════════════════════════════════════════════════════════════════════

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TelegramWebAppLoginRequest(BaseModel):
    init_data: str = Field(..., min_length=1)