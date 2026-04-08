from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    BigInteger, Integer, String, Boolean,
    Numeric, Float, DateTime, ForeignKey, Enum
)
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.config import Base


class User(Base):
    __tablename__ = "users"

    id:         Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username:   Mapped[str | None] = mapped_column(String(32))
    full_name:  Mapped[str] = mapped_column(String(128))
    is_active:  Mapped[bool] = mapped_column(default=True)
    language:   Mapped[str]  = mapped_column(String(2), default="uz")
    is_banned:  Mapped[bool] = mapped_column(default=False)
    role:       Mapped[str | None] = mapped_column(String(20), default="guest")
    phone_number: Mapped[str | None] = mapped_column(String(20))
    balance:    Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    created_at: Mapped[datetime] =mapped_column(DateTime,
        server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    driver = relationship("Driver", back_populates="user", uselist=False, cascade="all, delete-orphan")



class TruckType(Base):
    __tablename__ = "truck_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    max_weight: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    max_volume: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    length: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    width: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    height: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)
    pallet_capacity: Mapped[int] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(String(200), nullable=True)

    drivers: Mapped[list["Driver"]] = relationship("Driver", back_populates="truck_type_obj")

    def __repr__(self) -> str:
        return f"<TruckType(id={self.id}, name='{self.name}')>"

class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)

    truck_type: Mapped[TruckType] = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=False)
    truck_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    capacity_ton: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)
    capacity_m3: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)

    current_city: Mapped[str] = mapped_column(String(300), index=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.0)
    total_trips: Mapped[int] = mapped_column(Integer, default=0)
    docs_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    is_live_location_active: Mapped[bool] = mapped_column(Boolean, default=False)
    live_location_expires: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_latitude: Mapped[float] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[float] = mapped_column(Float, nullable=True)
    last_location_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="driver")

    def __repr__(self) -> str:
        return f"<Driver(id={self.id}, truck_number='{self.truck_number}', type='{self.truck_type}')>"

