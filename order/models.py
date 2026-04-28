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


class OrderStatus(enum.Enum):
    PENDING     = "pending"
    ACCEPTED    = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    CANCELLED   = "cancelled"



class WaypointType(enum.Enum):
    PICKUP   = "pickup"    # Yuk olinadigan joy
    DELIVERY = "delivery"  # Yuk tushiriladigan joy
    TRANSIT  = "transit"   # Oraliq to'xtash (dam olish, tekshiruv va h.k.)


class WaypointStatus(enum.Enum):
    PENDING   = "pending"    # Hali yetilmagan
    ARRIVED   = "arrived"    # Haydovchi yetib keldi
    COMPLETED = "completed"  # Ish tugadi (yuk olindi yoki tushirildi)
    SKIPPED   = "skipped"    # O'tkazib yuborildi


# ═══════════════════════════════════════════════
# ORDER
# ═══════════════════════════════════════════════

class Order(Base):
    __tablename__ = "orders"

    id          : Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id : Mapped[int]   = mapped_column(BigInteger, ForeignKey("users.id"),       nullable=False)
    driver_id   : Mapped[int | None] = mapped_column(Integer, ForeignKey("drivers.id"),   nullable=True)

    cargo_name  : Mapped[str]   = mapped_column(String(200), nullable=False)
    weight      : Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    volume      : Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    # Umumiy masofa — barcha waypoint oralig'i yig'indisi (avtomatik hisoblanadi)
    total_distance_km : Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    required_truck_type_id : Mapped[int] = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=False)

    price    : Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency : Mapped[str]   = mapped_column(String(10), default="UZS")

    # pickup_date / delivery_date → endi waypointlar da saqlanadi
    # Umumiy vaqt oralig'i (qulaylik uchun saqlab qo'yamiz)
    scheduled_start : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scheduled_end   : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status : Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )

    created_at : Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at : Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                  onupdate=lambda: datetime.now(timezone.utc))

    # ── Relationships ────────────────────────────
    customer   = relationship("User",      foreign_keys=[customer_id], backref="customer_orders")
    driver     = relationship("Driver",    foreign_keys=[driver_id],   backref="driver_orders")
    truck_type = relationship("TruckType")

    waypoints  : Mapped[list["OrderWaypoint"]] = relationship(
        "OrderWaypoint",
        back_populates="order",
        order_by="OrderWaypoint.sequence",   # har doim tartibli keladi
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

    # ── Helper property lar ──────────────────────

    @property
    def origin(self) -> "OrderWaypoint | None":
        """Birinchi nuqta (pickup)"""
        return self.waypoints[0] if self.waypoints else None

    @property
    def destination(self) -> "OrderWaypoint | None":
        """Oxirgi nuqta (delivery)"""
        return self.waypoints[-1] if self.waypoints else None

    @property
    def transit_stops(self) -> list["OrderWaypoint"]:
        """Oraliq nuqtalar"""
        return self.waypoints[1:-1] if len(self.waypoints) > 2 else []

    @property
    def current_waypoint(self) -> "OrderWaypoint | None":
        """Hozirgi faol nuqta"""
        for wp in self.waypoints:
            if wp.status == WaypointStatus.PENDING:
                return wp
        return None

    def __repr__(self) -> str:
        stops = len(self.waypoints) if self.waypoints else 0
        return f"<Order(id={self.id}, cargo='{self.cargo_name}', stops={stops}, status={self.status})>"


# ═══════════════════════════════════════════════
# ORDER WAYPOINT — Har bir to'xtash nuqtasi
# ═══════════════════════════════════════════════

class OrderWaypoint(Base):
    __tablename__ = "order_waypoints"

    id       : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id : Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)

    # Tartib raqami: 1 → 2 → 3 → ... (shu tartibda boriladi)
    sequence : Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # Nuqta turi
    waypoint_type : Mapped[WaypointType] = mapped_column(
        SQLEnum(WaypointType), nullable=False
    )

    # Manzil
    city        : Mapped[str]        = mapped_column(String(100), nullable=False, index=True)
    address     : Mapped[str | None] = mapped_column(String(300), nullable=True)
    landmark    : Mapped[str | None] = mapped_column(String(200), nullable=True)  # Mo'ljal

    # GPS koordinatalar
    latitude    : Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude   : Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)

    # Oldingi nuqtadan bu nuqtagacha masofa (km)
    distance_from_prev_km : Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    # Vaqt
    scheduled_arrival   : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Rejalashtirilgan
    actual_arrival      : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # Haqiqiy
    scheduled_departure : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_departure    : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # To'xtash muddati (daqiqalarda): yuk ortish/tushirish uchun
    stop_duration_min : Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Kontakt (yuk oluvchi/beruvchi)
    contact_name  : Mapped[str | None] = mapped_column(String(150), nullable=True)
    contact_phone : Mapped[str | None] = mapped_column(String(20),  nullable=True)

    # Izoh
    note   : Mapped[str | None] = mapped_column(Text, nullable=True)
    status : Mapped[WaypointStatus] = mapped_column(
        SQLEnum(WaypointStatus), default=WaypointStatus.PENDING, nullable=False
    )

    created_at : Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at : Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                  onupdate=lambda: datetime.now(timezone.utc))

    # ── Relationships ────────────────────────────
    order : Mapped["Order"] = relationship("Order", back_populates="waypoints")

    # ── Helper property lar ──────────────────────

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
            f"city='{self.city}', type={self.waypoint_type.value}, status={self.status.value})>"
        )


# ═══════════════════════════════════════════════
# ORDER OFFER
# ═══════════════════════════════════════════════




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

    # ── Narx ────────────────────────────────────────────────────────────────
    offered_price    : Mapped[float]          = mapped_column(Numeric(12, 2), nullable=False)
    currency         : Mapped[str]            = mapped_column(String(10),     default="UZS")

    # Mijoz qarshi taklif bersa (muzokarа)
    counter_price    : Mapped[float | None]   = mapped_column(Numeric(12, 2), nullable=True)
    counter_comment  : Mapped[str | None]     = mapped_column(String(500),    nullable=True)
    counter_at       : Mapped[datetime | None]= mapped_column(DateTime,       nullable=True)

    # ── Vaqt ────────────────────────────────────────────────────────────────
    # Birinchi nuqtaga (yuk olish) qachon yetib boradi
    estimated_pickup_time    : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Oxirgi nuqtaga (yetkazib berish) taxminiy vaqt
    estimated_delivery_time  : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Taklif qancha vaqt amal qiladi (shu vaqtdan keyin EXPIRED bo'ladi)
    expires_at : Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ── Haydovchining hozirgi holati ────────────────────────────────────────
    # Taklif berilgan paytda haydovchi qayerda edi (GPS)
    driver_latitude  : Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    driver_longitude : Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)

    # Buyurtma birinchi nuqtasiga taxminiy masofa (km)
    distance_to_pickup_km : Mapped[float | None] = mapped_column(Numeric(7, 2), nullable=True)

    # Qaysi yuk mashinasi bilan boradi
    truck_id : Mapped[int | None] = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=True)

    # ── Qo'shimcha ──────────────────────────────────────────────────────────
    comment : Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Haydovchi reytingi taklif berilgan paytda (snapshot — keyin o'zgarishi mumkin)
    driver_rating_snapshot : Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)

    # Haydovchi bu kategoriyada nechta muvaffaqiyatli yetkazib bergan (snapshot)
    driver_completed_orders_snapshot : Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Mijoz bu taklifni ko'rdimi
    is_seen       : Mapped[bool]          = mapped_column(Boolean, default=False)
    seen_at       : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    # ── Status ──────────────────────────────────────────────────────────────
    status : Mapped[OfferStatus] = mapped_column(
        SQLEnum(OfferStatus), default=OfferStatus.PENDING, nullable=False, index=True
    )

    # Status o'zgargan sabab (rad etilsa nima uchun)
    status_reason : Mapped[str | None] = mapped_column(String(300), nullable=True)

    # ── Timestamps ──────────────────────────────────────────────────────────
    created_at  : Mapped[datetime]          = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at  : Mapped[datetime]          = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                            onupdate=lambda: datetime.now(timezone.utc))
    accepted_at : Mapped[datetime | None]   = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None]   = mapped_column(DateTime, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    order  : Mapped["Order"]  = relationship("Order",  back_populates="offers")
    driver : Mapped["Driver"] = relationship("Driver", back_populates="offers")

    # ── Helper property lar ──────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """Taklif hali amal qiladimi"""
        if self.status not in (OfferStatus.PENDING, OfferStatus.SEEN):
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    @property
    def final_price(self) -> float:
        """
        Muzokara bo'lsa counter_price, bo'lmasa offered_price.
        Qabul qilingan narx shu.
        """
        return float(self.counter_price or self.offered_price)

    @property
    def response_time_minutes(self) -> int | None:
        """Mijoz qancha vaqtda qaror qildi (daqiqalarda)"""
        if self.accepted_at and self.created_at:
            delta = self.accepted_at - self.created_at
            return int(delta.total_seconds() / 60)
        return None

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