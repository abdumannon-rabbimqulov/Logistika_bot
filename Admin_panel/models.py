from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from config.base import Base


class PlatformSettings(Base):
    """Tizim darajasidagi sozlamalar — yagona qator (id=1). Hozircha faqat komissiya foizi."""

    __tablename__ = "platform_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Har bir COMPLETED order uchun haydovchi balansidan yechiladigan foiz (0-100)
    commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("10.00"))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
