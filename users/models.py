from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    BigInteger, String, Numeric, DateTime
)

from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.config import Base

class User(Base):
    __tablename__ = "users"

    id:         Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username:   Mapped[str | None] = mapped_column(String(32),nullable=True)
    full_name:  Mapped[str] = mapped_column(String(128))
    password:   Mapped[str] = mapped_column(String(), nullable=True)
    is_active:  Mapped[bool] = mapped_column(default=True)
    language:   Mapped[str]  = mapped_column(String(2), default="uz")
    is_banned:  Mapped[bool] = mapped_column(default=False)
    role:       Mapped[str | None] = mapped_column(String(20), default="guest")
    phone_number: Mapped[str | None] = mapped_column(String(20))
    balance:    Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )
    token: Mapped[str | None] = mapped_column(String(), nullable=True)
    token_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    driver = relationship("Driver", back_populates="user", uselist=False, cascade="all, delete-orphan")

