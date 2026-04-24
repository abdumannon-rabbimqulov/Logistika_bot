from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator



class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"



class LoginRequest(BaseModel):

    phone_number: Optional[str] = Field(None, max_length=20)
    password: str

    @model_validator(mode="after")
    def check_identifier(self):
        if not self.phone_number:
            raise ValueError("phone_number kiritilishi shart.")
        return self



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



class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=128)
    phone_number: Optional[str] = Field(None, max_length=20)
    language: Optional[str] = Field(None, min_length=2, max_length=2)



class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TelegramWebAppLoginRequest(BaseModel):
    init_data: str = Field(..., min_length=1)