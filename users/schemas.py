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




class UserTariffPaymentCreate(BaseModel):

    user_id: int = Field(...)
    billing_year: int = Field(..., ge=2000, le=2100)
    billing_month: int = Field(..., ge=1, le=12)
    amount: Decimal = Field(..., ge=0, description="To‘langan summa")
    currency: str = Field(default="UZS", max_length=10)
    tariff_code: Optional[str] = Field(None, max_length=64, description="Masalan: basic, pro")
    paid_at: Optional[datetime] = None
    note: Optional[str] = None


class UserTariffPaymentUpdate(BaseModel):
    billing_year: Optional[int] = Field(None, ge=2000, le=2100)
    billing_month: Optional[int] = Field(None, ge=1, le=12)
    amount: Optional[Decimal] = Field(None, ge=0)
    currency: Optional[str] = Field(None, max_length=10)
    tariff_code: Optional[str] = Field(None, max_length=64)
    paid_at: Optional[datetime] = None
    note: Optional[str] = None


class UserTariffPaymentRead(BaseModel):
    id: int
    user_id: int
    billing_month: date
    amount: Decimal
    currency: str
    tariff_code: Optional[str]
    paid_at: Optional[datetime]
    note: Optional[str]
    recorded_by_admin_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserMonthlyTariffSummary(BaseModel):

    billing_month: date
    total_amount: Decimal
    payment_count: int
    currency: str