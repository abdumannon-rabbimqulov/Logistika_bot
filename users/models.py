from __future__ import annotations
import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, String, Numeric, DateTime, ForeignKey, Enum, Boolean, Integer, Text
)
from config.config import Base

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.models import Chat,Rating,AICommand

class UserRole(str, enum.Enum):
    ADMIN  = "admin"
    SENDER = "sender"
    DRIVER = "driver"
    GUEST  = "guest"


# ═══════════════════════════════════════════════════════════════════════════
# EMAIL OTP — Tasdiqlash kodlari (DB da saqlanadi)
# ═══════════════════════════════════════════════════════════════════════════

class EmailOTP(Base):
    __tablename__ = "email_otps"

    id         : Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    email      : Mapped[str]           = mapped_column(String(254), nullable=False, index=True)
    code       : Mapped[str]           = mapped_column(String(10),  nullable=False)

    hashed_pw  : Mapped[str]           = mapped_column(Text, nullable=False)
    full_name  : Mapped[str]           = mapped_column(String(128), nullable=False)
    language   : Mapped[str]           = mapped_column(String(10),  default="uz")

    is_used    : Mapped[bool]          = mapped_column(Boolean, default=False)
    expires_at : Mapped[datetime]      = mapped_column(DateTime, nullable=False)
    created_at : Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())

    def is_valid(self) -> bool:
        """Kod muddati o'tmagan va hali ishlatilmagan."""
        return not self.is_used and datetime.utcnow() < self.expires_at



class User(Base):
    __tablename__ = "users"

    id:         Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username:   Mapped[str | None] = mapped_column(String(32), nullable=True)
    full_name:  Mapped[str] = mapped_column(String(128))
    password:   Mapped[str] = mapped_column(String(), nullable=True)
    is_active:  Mapped[bool] = mapped_column(default=True)
    language:   Mapped[str]  = mapped_column(String(10), default="uz")
    is_banned:  Mapped[bool] = mapped_column(default=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="userrole",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=UserRole.GUEST,
        server_default=UserRole.GUEST.value
    )

    phone_number: Mapped[str | None] = mapped_column(String(20))
    email:        Mapped[str | None] = mapped_column(String(100), unique=True)
    balance:    Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.0)
    bio:        Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    driver = relationship("Driver", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chats            : Mapped[list["Chat"]]      = relationship(back_populates="user" )
    ratings_given: Mapped[list["Rating"]] = relationship(
        foreign_keys="[Rating.rated_by_user]",
        back_populates="rater_user")
    ratings_received: Mapped[list["Rating"]] = relationship(
        foreign_keys="[Rating.target_user]",
        back_populates="target_user_obj")
    ai_commands: Mapped[list["AICommand"]] = relationship(back_populates="user")

