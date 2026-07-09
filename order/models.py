from __future__ import annotations
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Integer, String, Numeric, DateTime,
    ForeignKey, Enum as SQLEnum, Text, SmallInteger, Boolean, JSON, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.config import Base
from utils.db_types import CaseInsensitiveEnum

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.models import Chat, Rating
    from driver.models import Driver


class Region(Base):

    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    soato_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    name_uz: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    name_oz: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name_ru: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name_en: Mapped[str | None] = mapped_column(String(120), nullable=True)
    slug: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)

    centroid_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    centroid_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    bounds: Mapped[list | None] = mapped_column(JSON, nullable=True)
    geojson: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    districts: Mapped[list["District"]] = relationship(
        "District",
        back_populates="region",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Region(id={self.id}, name_uz='{self.name_uz}')>"


class District(Base):

    __tablename__ = "districts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_id: Mapped[int] = mapped_column(Integer, ForeignKey("regions.id", ondelete="CASCADE"), nullable=False, index=True)
    soato_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    name_uz: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    name_oz: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name_ru: Mapped[str | None] = mapped_column(String(120), nullable=True)
    name_en: Mapped[str | None] = mapped_column(String(120), nullable=True)
    slug: Mapped[str | None] = mapped_column(String(80), nullable=True)

    centroid_lat: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    centroid_lng: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    bounds: Mapped[list | None] = mapped_column(JSON, nullable=True)
    geojson: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    region: Mapped["Region"] = relationship("Region", back_populates="districts")

    def __repr__(self) -> str:
        return f"<District(id={self.id}, region_id={self.region_id}, name_uz='{self.name_uz}')>"


class OrderStatus(str, enum.Enum):

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"



class WaypointType(enum.Enum):
    PICKUP   = "PICKUP"
    DELIVERY = "DELIVERY"
    TRANSIT  = "TRANSIT"


class WaypointStatus(enum.Enum):
    PENDING   = "PENDING"
    ARRIVED   = "ARRIVED"
    COMPLETED = "COMPLETED"
    SKIPPED   = "SKIPPED"



class Order(Base):
    __tablename__ = "orders"

    id          : Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id : Mapped[int]   = mapped_column(BigInteger, ForeignKey("users.id"),       nullable=False)
    driver_id   : Mapped[int | None] = mapped_column(Integer, ForeignKey("drivers.id"),   nullable=True)

    cargo_name  : Mapped[str]   = mapped_column(String(200), nullable=False)
    weight      : Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    volume      : Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    total_distance_km : Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    required_truck_type_id : Mapped[int] = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=False)

    price    : Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency : Mapped[str]   = mapped_column(String(10), default="UZS")

    scheduled_start : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_end   : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(
            OrderStatus,
            name="orderstatus",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=OrderStatus.PENDING,
        nullable=False,
    )

    created_at : Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at : Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer   = relationship("User",      foreign_keys=[customer_id], backref="customer_orders")
    driver     = relationship("Driver",    foreign_keys=[driver_id],   backref="driver_orders")
    truck_type = relationship("TruckType")

    waypoints  : Mapped[list["OrderWaypoint"]] = relationship(
        "OrderWaypoint",
        back_populates="order",
        order_by="OrderWaypoint.sequence",
        cascade="all, delete-orphan",
    )

    offers     : Mapped[list["OrderOffer"]] = relationship(
        "OrderOffer",
        back_populates="order",
    )

    chat_id  : Mapped[int | None] = mapped_column(Integer, ForeignKey("chats.id"), nullable=True)

    chat       : Mapped["Chat"] = relationship(
        "Chat",
        foreign_keys=[chat_id],
        back_populates="orders"
    )

    rating     : Mapped["Rating"] = relationship(
        "Rating",
        back_populates="order",
        uselist=False,
    )

    tracks: Mapped[list["OrderTrack"]] = relationship(
        "OrderTrack",
        back_populates="order",
        order_by="OrderTrack.recorded_at",
        cascade="all, delete-orphan",
    )


    @property
    def origin(self) -> "OrderWaypoint | None":
        return self.waypoints[0] if self.waypoints else None

    @property
    def destination(self) -> "OrderWaypoint | None":
        return self.waypoints[-1] if self.waypoints else None

    @property
    def transit_stops(self) -> list["OrderWaypoint"]:
        return self.waypoints[1:-1] if len(self.waypoints) > 2 else []

    @property
    def current_waypoint(self) -> "OrderWaypoint | None":
        for wp in self.waypoints:
            if wp.status == WaypointStatus.PENDING:
                return wp
        return None




    def __repr__(self) -> str:
        _id = self.__dict__.get("id", "Unknown")
        _status = self.__dict__.get("status", "Unknown")
        return f"<Order(id={_id}, status={_status})>"






class OrderTrack(Base):
    __tablename__ = "order_tracks"

    id          : Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id    : Mapped[int]      = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    latitude    : Mapped[float]    = mapped_column(Numeric(9, 6), nullable=False)
    longitude   : Mapped[float]    = mapped_column(Numeric(9, 6), nullable=False)
    recorded_at : Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Order bilan teskari aloqa
    order       = relationship("Order", back_populates="tracks")

class OrderWaypoint(Base):
    __tablename__ = "order_waypoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    # Nuqtaning tartibi: 1 - yukni olish joyi, 2 - topshirish joyi (agar 3-4 bo'lsa, yo'l-yo'lakay tashlab o'tiladigan joylar)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)

    # Manzil matni va Yandex xaritasidan keladigan koordinatalar
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)

    # O'sha nuqtada yukni kim kutib oladi / kim topshiradi? (Kuryer/Haydovchi telefon qilishi uchun)
    contact_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20),  nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="waypoints")


