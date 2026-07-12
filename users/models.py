from __future__ import annotations
import enum
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.schema import Index
from config.config import Base

from sqlalchemy import text

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional


class UserRole(str, enum.Enum):
    ADMIN  = "admin"
    SENDER = "sender"
    DRIVER = "driver"
    GUEST  = "guest"
    DISPATCHER = "dispatcher"
    MANAGER = "manager"



class User(Base):
    __tablename__ = "users"

    id:         Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username:   Mapped[str | None] = mapped_column(String(32), nullable=True)
    full_name:  Mapped[str] = mapped_column(String(128))
    password:   Mapped[str] = mapped_column(String(), nullable=True)
    is_active:  Mapped[bool] = mapped_column(default=True)
    language:   Mapped[str]  = mapped_column(String(10), default="uz")
    is_banned:  Mapped[bool] = mapped_column(default=False)
    banned_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
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

    tariff_payments: Mapped[list["UserTariffPayment"]] = relationship(
        back_populates="user",
        foreign_keys="UserTariffPayment.user_id",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserTariffPayment(Base):

    __tablename__ = "user_tariff_payments"

    __table_args__ = (Index("ix_user_tariff_payments_user_billing_month", "user_id", "billing_month"),)

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    billing_month: Mapped[date] = mapped_column(Date, nullable=False)

    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="UZS")
    tariff_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    recorded_by_admin_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(
        foreign_keys=[user_id],
        back_populates="tariff_payments",
    )

class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(String(6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now() + interval '2 minutes'"),
        nullable=False
    )