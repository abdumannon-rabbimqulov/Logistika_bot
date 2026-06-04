from __future__ import annotations
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Integer, String, Numeric, DateTime,
    ForeignKey, Enum as SQLEnum, Text, SmallInteger,Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from config.config import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.models import Chat, Rating
    from driver.models import Driver


class OrderStatus(str, enum.Enum):
    """PostgreSQL orderstatus enum — qiymatlar katta harfda saqlanadi."""

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"



class WaypointType(enum.Enum):
    PICKUP   = "pickup"    # Yuk olinadigan joy
    DELIVERY = "delivery"  # Yuk tushiriladigan joy
    TRANSIT  = "transit"   # Oraliq to'xtash (dam olish, tekshiruv va h.k.)


class WaypointStatus(enum.Enum):
    PENDING   = "pending"    # Kutilmoqda
    ARRIVED   = "arrived"    # Haydovchi yetib keldi
    COMPLETED = "completed"  # Ish tugadi (yuk olindi yoki tushirildi)
    SKIPPED   = "skipped"    # O'tkazib yuborildi




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

    created_at : Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at : Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                  onupdate=lambda: datetime.now(timezone.utc))

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

    chat       : Mapped["Chat"] = relationship(
        "Chat",
        back_populates="order",
        uselist=False,
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
        stops = len(self.waypoints) if self.waypoints else 0
        return f"<Order(id={self.id}, cargo='{self.cargo_name}', stops={stops}, status={self.status})>"






class OrderTrack(Base):
    __tablename__ = "order_tracks"

    id          : Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id    : Mapped[int]      = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    latitude    : Mapped[float]    = mapped_column(Numeric(9, 6), nullable=False)
    longitude   : Mapped[float]    = mapped_column(Numeric(9, 6), nullable=False)
    recorded_at : Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Order bilan teskari aloqa
    order       = relationship("Order", back_populates="tracks")


class OrderWaypoint(Base):
    __tablename__ = "order_waypoints"

    id       : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id : Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    sequence : Mapped[int] = mapped_column(SmallInteger, nullable=False)

    waypoint_type : Mapped[WaypointType] = mapped_column(
        SQLEnum(WaypointType), nullable=False
    )

    address     : Mapped[str | None] = mapped_column(String(300), nullable=True)
    landmark    : Mapped[str | None] = mapped_column(String(200), nullable=True)  # Mo'ljal

    latitude    : Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude   : Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)

    distance_from_prev_km : Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)


    scheduled_arrival   : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Rejalashtirilgan
    actual_arrival      : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Haqiqiy
    scheduled_departure : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_departure    : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    stop_duration_min : Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    contact_name  : Mapped[str | None] = mapped_column(String(150), nullable=True)
    contact_phone : Mapped[str | None] = mapped_column(String(20),  nullable=True)

    note   : Mapped[str | None] = mapped_column(Text, nullable=True)
    status : Mapped[WaypointStatus] = mapped_column(
        SQLEnum(WaypointStatus), default=WaypointStatus.PENDING, nullable=False
    )

    created_at : Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at : Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                  onupdate=lambda: datetime.now(timezone.utc))

    order : Mapped["Order"] = relationship("Order", back_populates="waypoints")


    @property
    def is_first(self) -> bool:
        return self.sequence == 1

    @property
    def delay_minutes(self) -> int | None:
        """Kechikish daqiqalarda (musbat = kech, manfiy = erta)"""
        if self.scheduled_arrival and self.actual_arrival:
            delta = self.actual_arrival - self.scheduled_arrival
            return int(delta.total_seconds() / 60)
        return None

    def __repr__(self) -> str:
        return (
            f"<Waypoint(order={self.order_id}, seq={self.sequence}, "
            f"address={self.address} type={self.waypoint_type.value}, status={self.status.value})>"
        )







class OfferStatus(enum.Enum):
    PENDING   = "pending"    # Haydovchi taklif berdi, mijoz ko'rmagan
    SEEN      = "seen"       # Mijoz ko'rdi, hali qaror qilmagan
    ACCEPTED  = "accepted"   # Mijoz qabul qildi → order shu haydovchiga beriladi
    REJECTED  = "rejected"   # Mijoz rad etdi
    CANCELLED = "cancelled"  # Haydovchi o'zi qaytarib oldi
    EXPIRED   = "expired"    # Muddati o'tib ketdi (cron job belgilaydi)
    OUTBID    = "outbid"     # Boshqa taklif qabul qilindi (avtomatik)


class OrderOffer(Base):
    __tablename__ = "order_offers"

    id        : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id  : Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"),   nullable=False, index=True)
    driver_id : Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id"),  nullable=False, index=True)

    offered_price    : Mapped[float]          = mapped_column(Numeric(12, 2), nullable=False)
    currency         : Mapped[str]            = mapped_column(String(10),     default="UZS")

    estimated_pickup_time    : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    estimated_delivery_time  : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    expires_at : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


    distance_to_pickup_km : Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)

    comment : Mapped[str | None] = mapped_column(String(500), nullable=True)


    is_seen       : Mapped[bool]          = mapped_column(Boolean, default=False)
    seen_at       : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    status : Mapped[OfferStatus] = mapped_column(
        SQLEnum(OfferStatus), default=OfferStatus.PENDING, nullable=False, index=True
    )

    status_reason : Mapped[str | None] = mapped_column(String(300), nullable=True)

    created_at  : Mapped[datetime]          = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  : Mapped[datetime]          = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                            onupdate=lambda: datetime.now(timezone.utc))
    accepted_at : Mapped[datetime | None]   = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None]   = mapped_column(DateTime, nullable=True)

    order  : Mapped["Order"]  = relationship("Order",  back_populates="offers")
    driver : Mapped["Driver"] = relationship("Driver", back_populates="offers")


    @property
    def is_active(self) -> bool:
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True



    def mark_seen(self) -> None:
        self.is_seen = True
        self.seen_at = datetime.now(timezone.utc)
        if self.status == OfferStatus.PENDING:
            self.status = OfferStatus.SEEN

    def accept(self) -> None:
        self.status = OfferStatus.ACCEPTED
        self.accepted_at = datetime.now(timezone.utc)

    def reject(self, reason: str | None = None) -> None:
        self.status = OfferStatus.REJECTED
        self.status_reason = reason

    def cancel(self, reason: str | None = None) -> None:
        self.status = OfferStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)
        self.status_reason = reason

    def __repr__(self) -> str:
        return (
            f"<OrderOffer(id={self.id}, order={self.order_id}, "
            f"driver={self.driver_id}, price={self.offered_price}, "
            f"status={self.status.value})>"
        )