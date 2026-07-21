from datetime import datetime, date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator



class Token(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"








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

    @field_validator("phone_number", mode="before")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        from utils.validation import normalize_phone_number
        return normalize_phone_number(v)




class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TelegramWebAppLoginRequest(BaseModel):
    init_data: str = Field(..., min_length=1)


class RoleSelectRequest(BaseModel):
    """Ro'yxatdan o'tishda GUEST o'z rolini birinchi marta tanlaydi (Mini App uchun).

    Faqat SENDER/DRIVER ruxsat etiladi — ADMIN/DISPATCHER/MANAGER kabi rollarni
    hech kim o'ziga o'zi tayinlay olmasligi kerak (bu faqat admin panel ishi).
    """
    role: Literal["sender", "driver"]
