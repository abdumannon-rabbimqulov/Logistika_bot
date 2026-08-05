"""Support mikroservizining o'z modellari (alohida `support_db` bazasida).

Asosiy tizim jadvallariga FK YO'Q va bo'lishi ham mumkin emas — bu boshqa baza.
`user_id` / `order_id` — shunchaki tashqi tizimning identifikatorlari (nusxa
ma'lumot). Bu mikroservizlar uchun odatiy: chegara bazalar orasidan o'tadi,
bog'lanish esa ID va hodisalar orqali.

MOLIYAVIY MAYDON YO'Q: bu yerda na narx, na balans, na komissiya saqlanadi —
menejer support bo'limida ham hech qanday pul ma'lumotini ko'rmaydi.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# Yopilgan murojaatga yangi xabar yozilmaydi — aks holda "yopildi" degan holat
# ma'nosini yo'qotardi va yopilgan ish qayta jonlanib ketardi.
CLOSED_STATUSES = frozenset({TicketStatus.RESOLVED, TicketStatus.CLOSED})


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Asosiy tizimdagi foydalanuvchi ID si (Telegram ID bo'lgani uchun BigInteger).
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    # Murojaat yozilgan paytdagi roli — keyin o'zgarsa ham tarix saqlanadi.
    user_role: Mapped[str | None] = mapped_column(String(20), nullable=True)

    order_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(
            TicketStatus,
            name="ticketstatus",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=TicketStatus.OPEN,
        nullable=False,
        index=True,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        SQLEnum(
            TicketPriority,
            name="ticketpriority",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        default=TicketPriority.NORMAL,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    messages: Mapped[list["SupportMessage"]] = relationship(
        "SupportMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="SupportMessage.created_at",
    )


class SupportMessage(Base):
    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # `is_system=True` bo'lganda muallif yo'q — xabar RabbitMQ hodisasidan tug'ilgan
    # (masalan "buyurtma holati IN_PROGRESS ga o'zgardi").
    author_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    author_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped["SupportTicket"] = relationship("SupportTicket", back_populates="messages")
