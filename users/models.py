import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional
from ai.models import Chat,Rating,AICommand

from sqlalchemy import (
    BigInteger, String, Numeric, DateTime, ForeignKey, Enum
)

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.config import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SENDER = "sender"
    DRIVER = "driver"
    GUEST = "guest"



class User(Base):
    __tablename__ = "users"

    id:         Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username:   Mapped[str | None] = mapped_column(String(32),nullable=True)
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
    balance:    Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.0)
    bio:        Mapped[str| None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

    driver = relationship("Driver", back_populates="user", uselist=False, cascade="all, delete-orphan")
    chats            : Mapped[list["Chat"]]      = relationship(back_populates="user",   lazy="select")
    ratings_given: Mapped[list["Rating"]] = relationship(
        foreign_keys="[Rating.rated_by_user]",
        back_populates="rater_user", lazy="select")
    ratings_received: Mapped[list["Rating"]] = relationship(
        foreign_keys="[Rating.target_user]",
        back_populates="target_user_obj", lazy="select")
    ai_commands: Mapped[list["AICommand"]] = relationship(back_populates="user", lazy="select")
