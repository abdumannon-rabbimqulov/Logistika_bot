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
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.schema import Index
from config.base import Base

from sqlalchemy import text

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from driver.models import Driver
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

    driver: Mapped[Optional["Driver"]] = relationship("Driver", back_populates="user", uselist=False, cascade="all, delete-orphan")



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


class BalanceTransactionType(str, enum.Enum):
    ORDER_COMMISSION  = "ORDER_COMMISSION"   # tizim komissiyasi — order COMPLETED bo'lganda avtomatik yechiladi
    ADMIN_ADJUSTMENT  = "ADMIN_ADJUSTMENT"   # admin qo'lda balansni o'zgartirdi (to'ldirish/tuzatish)


class BalanceTransaction(Base):
    """Balans o'zgarishlari tarixi (audit) — komissiya yechilishi va admin tuzatishlari shu yerda loglanadi."""

    __tablename__ = "balance_transactions"

    __table_args__ = (Index("ix_balance_transactions_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    type: Mapped[BalanceTransactionType] = mapped_column(
        Enum(
            BalanceTransactionType,
            name="balancetransactiontype",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )

    # Ishorali: manfiy = balansdan yechildi (komissiya), musbat = balansga qo'shildi (to'ldirish/tuzatish)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    order_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="SET NULL"), nullable=True
    )
    created_by_admin_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])