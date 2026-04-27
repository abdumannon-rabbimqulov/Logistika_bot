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
# EMAIL RO'YXATDAN O'TISH — 1-qadam
# ═══════════════════════════════════════════════════════════════════════════

class EmailRegisterRequest(BaseModel):
    """Email, parol va to'liq ism → OTP email ga yuboriladi."""
    email:     EmailStr      = Field(..., description="Foydalanuvchi email manzili")
    password:  str           = Field(..., min_length=8, description="Kamida 8 ta belgi")
    full_name: str           = Field(..., min_length=2, max_length=128, description="To'liq ism")
    language:  Optional[str] = Field("uz", min_length=2, max_length=10)


# ═══════════════════════════════════════════════════════════════════════════
# EMAIL TASDIQLASH — 2-qadam
# ═══════════════════════════════════════════════════════════════════════════

class EmailVerifyRequest(BaseModel):
    """Email + OTP kodi → akkaunt yaratiladi, token qaytariladi."""
    email: EmailStr = Field(..., description="Ro'yxatdan o'tilayotgan email")
    code:  str      = Field(..., min_length=4, max_length=10, description="Email ga kelgan OTP kodi")


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
# DRIVER PROFILI TO'LDIRISH — 4-qadam (faqat driver uchun)
# ═══════════════════════════════════════════════════════════════════════════

class DriverProfileRequest(BaseModel):
    """
    Driver ro'yxatdan o'tganda to'ldirishi kerak bo'lgan ma'lumotlar.
    truck_type_id: truck_types jadvalidagi ID (GET /api/drivers/truck-types dan olish mumkin)
    """
    truck_type_id: int   = Field(..., description="Yuk mashinasi turi ID si")
    truck_number:  str   = Field(..., min_length=3, max_length=20, description="Davlat raqami (60A123BC)")
    truck_brand:   Optional[str]   = Field(None, max_length=100, description="Brend (Mercedes, Volvo...)")
    truck_year:    Optional[int]   = Field(None, ge=1980, le=2030, description="Ishlab chiqarilgan yil")
    capacity_ton:  Optional[float] = Field(None, gt=0, description="Sig'im (tonna)")
    capacity_m3:   Optional[float] = Field(None, gt=0, description="Sig'im (m³)")
    current_city:  str             = Field(..., min_length=2, max_length=100, description="Hozirgi shahar")
    phone_number:  Optional[str]   = Field(None, max_length=20, description="Aloqa raqami")


# ═══════════════════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════════════════

class EmailLoginRequest(BaseModel):
    """Email va parol orqali tizimga kirish."""
    email:    EmailStr = Field(..., description="Email manzil")
    password: str      = Field(..., min_length=1, description="Parol")


class LoginRequest(BaseModel):
    """Telefon raqam va parol orqali login (eski usul)."""
    phone_number: Optional[str] = Field(None, max_length=20)
    password: str

    @model_validator(mode="after")
    def check_identifier(self):
        if not self.phone_number:
            raise ValueError("phone_number kiritilishi shart.")
        return self


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