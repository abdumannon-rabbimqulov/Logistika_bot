"""Avtomatik dispatch: bitta buyurtma uchun ketma-ket haydovchilarga yuborilgan takliflar.

Bir vaqtning o'zida bitta order uchun faqat bitta `pending` attempt bo'ladi (navbat bilan
ishlaydi) — shu sababli eski `assign-driver` ochiq ro'yxatidagi poyga sharoiti (race condition)
bu yerda tabiiy ravishda yo'q: ikkinchi haydovchiga umuman taklif yuborilmagan bo'ladi.
Qarang: docs/DISPATCH_SYSTEM_PLAN.md
"""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.base import Base


class DispatchMatchType(str, enum.Enum):
    GPS = "gps"        # Tier A — jonli GPS bo'yicha eng yaqin
    REGION = "region"  # Tier B — GPS yo'q, region/shahar matn moslik bo'yicha fallback


class DispatchAttemptStatus(str, enum.Enum):
    PENDING = "pending"      # Haydovchiga yuborilgan, javob kutilmoqda (60s)
    ACCEPTED = "accepted"    # Haydovchi qabul qildi
    REJECTED = "rejected"    # Haydovchi rad etdi
    EXPIRED = "expired"      # 60s ichida javob bermadi
    CANCELLED = "cancelled"  # Boshqa sabab bilan bekor qilindi (masalan order o'chirildi)


class DispatchAttempt(Base):
    __tablename__ = "dispatch_attempts"

    __table_args__ = (
        Index("ix_dispatch_attempts_order_status", "order_id", "status"),
        Index("ix_dispatch_attempts_driver_status", "driver_id", "status"),
        Index("ix_dispatch_attempts_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)

    round_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    match_type: Mapped[DispatchMatchType] = mapped_column(
        SQLEnum(
            DispatchMatchType,
            name="dispatchmatchtype",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    status: Mapped[DispatchAttemptStatus] = mapped_column(
        SQLEnum(
            DispatchAttemptStatus,
            name="dispatchattemptstatus",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=DispatchAttemptStatus.PENDING,
        nullable=False,
    )

    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Bot xabarini keyinroq edit qilish uchun (masalan "vaqt tugadi"/"qabul qilindi")
    bot_chat_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bot_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    order: Mapped["Order"] = relationship("Order")  # noqa: F821
    driver: Mapped["Driver"] = relationship("Driver")  # noqa: F821

    def __repr__(self) -> str:
        _id = self.__dict__.get("id", "Unknown")
        return f"<DispatchAttempt(id={_id}, order_id={self.order_id}, driver_id={self.driver_id}, status={self.status})>"
