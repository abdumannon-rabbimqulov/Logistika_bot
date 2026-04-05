from sqlalchemy import DateTime, func
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import (
    BigInteger, Integer, String, Boolean,
    Numeric, Float, DateTime, ForeignKey, Enum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config import Base


class User(Base):
    __tablename__ = "users"

    id:         Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username:   Mapped[str | None] = mapped_column(String(32))
    full_name:  Mapped[str] = mapped_column(String(128))
    is_active:  Mapped[bool] = mapped_column(default=True)
    language:   Mapped[str]  = mapped_column(String(2), default="uz")
    is_banned:  Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] =mapped_column(DateTime,
        server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )



class TruckType(PyEnum):
    TENT = "tent"
    REF = "ref"
    BORT = "bort"
    CONTAINER = "container"
    SILOS = "silos"


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)

    # Mashina ma'lumotlari
    truck_type: Mapped[TruckType] = mapped_column(Enum(TruckType), nullable=False)
    truck_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # Yuk ko'tarish imkoniyati (Tonnalarda va Kub metrlarda)
    capacity_ton: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    capacity_m3: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)

    # Holat va Reyting
    current_city: Mapped[str] = mapped_column(String(100), index=True)  # Shahar bo'yicha tez qidirish uchun
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.0)
    total_trips: Mapped[int] = mapped_column(Integer, default=0)
    docs_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Live Lokatsiya (Haqiqiy vaqtdagi joylashuv)
    is_live_location_active: Mapped[bool] = mapped_column(Boolean, default=False)
    live_location_expires: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_latitude: Mapped[float] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[float] = mapped_column(Float, nullable=True)
    last_location_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Avtomatik vaqt qaydlari
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))

    # Bog'lanishlar (Relationships)
    user = relationship("User", back_populates="driver")
    announces = relationship("DriverAnnounce", back_populates="driver", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="driver")
    location_history = relationship("DriverLocation", back_populates="driver", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Driver(id={self.id}, truck_number='{self.truck_number}', type='{self.truck_type}')>"