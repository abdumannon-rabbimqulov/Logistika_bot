import enum
from datetime import datetime, timezone
from typing import Optional
from ai.models import Chat,Rating
from sqlalchemy import (
    BigInteger, Integer, String, Boolean,
    Numeric, Float, DateTime, ForeignKey, Enum as SQLEnum, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.config import Base
from order.models import OrderOffer


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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


    drivers: Mapped[list["Driver"]] = relationship("Driver", back_populates="truck_type_obj")

    def __repr__(self) -> str:
        return f"<TruckType(id={self.id}, name='{self.name}')>"


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)

    truck_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=False)
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

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(),
                                                 onupdate=func.now())

    user = relationship("User", back_populates="driver")
    truck_type_obj: Mapped["TruckType"] = relationship("TruckType", back_populates="drivers")
    announcements: Mapped[list["DriverAnnouncement"]] = relationship("DriverAnnouncement", back_populates="driver")

    # ✅ FIX 3: OrderOffer.driver back_populates="offers" uchun relationship qo'shildi
    offers: Mapped[list["OrderOffer"]] = relationship("OrderOffer", back_populates="driver")
    chats: Mapped[list["Chat"]] = relationship(back_populates="driver", lazy="select")
    ratings_given: Mapped[list["Rating"]] = relationship(
        foreign_keys="[Rating.rated_by_driver]",
        back_populates="rater_driver", lazy="select")
    ratings_received: Mapped[list["Rating"]] = relationship(
        foreign_keys="[Rating.target_driver]",
        back_populates="target_driver_obj", lazy="select")

    def __repr__(self) -> str:
        return f"<Driver(id={self.id}, truck_number='{self.truck_number}', type='{self.truck_type_id}')>"


class DriverAnnouncement(Base):
    __tablename__ = "driver_announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id"), nullable=False)

    from_city: Mapped[str] = mapped_column(String(), nullable=False, index=True)
    to_city: Mapped[str] = mapped_column(String(), nullable=False, index=True)

    departure_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(),
                                                 onupdate=func.now())

    driver = relationship("Driver", back_populates="announcements")
    offers: Mapped[list["AnnouncementOffer"]] = relationship("AnnouncementOffer", back_populates="announcement")

    def __repr__(self) -> str:
        return f"<Announcement(from='{self.from_city}', to='{self.to_city}', active={self.is_active})>"


class AnnouncementOfferStatus(enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class AnnouncementOffer(Base):
    __tablename__ = "announcement_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id: Mapped[int] = mapped_column(Integer, ForeignKey("driver_announcements.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    cargo_description: Mapped[str] = mapped_column(String(500), nullable=False)
    offered_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[AnnouncementOfferStatus] = mapped_column(
        SQLEnum(AnnouncementOfferStatus), default=AnnouncementOfferStatus.PENDING, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    announcement = relationship("DriverAnnouncement", back_populates="offers")
    customer = relationship("User")

    def __repr__(self) -> str:
        return f"<AnnOffer(id={self.id}, price={self.offered_price}, status={self.status})>"