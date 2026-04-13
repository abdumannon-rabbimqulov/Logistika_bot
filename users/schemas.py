from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ──────────────────────────────────────────────
#  TOKEN
# ──────────────────────────────────────────────
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ──────────────────────────────────────────────
#  LOGIN
# ──────────────────────────────────────────────
class LoginRequest(BaseModel):
    """
    Login uchun phone_number yoki username + password.
    Ikkalasidan kamida biri bo'lishi shart.
    """
    phone_number: Optional[str] = Field(None, max_length=20)
    username: Optional[str] = Field(None, max_length=32)
    password: str

    @model_validator(mode="after")
    def check_identifier(self):
        if not self.phone_number and not self.username:
            raise ValueError("phone_number yoki username kiritilishi shart.")
        return self


# ──────────────────────────────────────────────
#  USER READ
# ──────────────────────────────────────────────
class UserRead(BaseModel):
    id: int
    username: Optional[str]
    full_name: str
    phone_number: Optional[str]
    role: Optional[str]
    language: str
    is_active: bool
    is_banned: bool
    balance: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ──────────────────────────────────────────────
#  USER UPDATE (profil tahrirlash)
# ──────────────────────────────────────────────
class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=128)
    username: Optional[str] = Field(None, max_length=32)
    phone_number: Optional[str] = Field(None, max_length=20)
    language: Optional[str] = Field(None, min_length=2, max_length=2)


# ──────────────────────────────────────────────
#  CHANGE PASSWORD
# ──────────────────────────────────────────────
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6)