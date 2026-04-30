from __future__ import annotations
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Integer, String, Boolean,
    Numeric, Float, DateTime, ForeignKey,
    Enum as SQLEnum, Text, SmallInteger, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.config import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai.models import Chat,Rating
    from order.models import OrderOffer
# ═══════════════════════════════════════════════
# ENUM lar
# ═══════════════════════════════════════════════

class AnnouncementOfferStatus(enum.Enum):
    PENDING   = "pending"
    SEEN      = "seen"
    ACCEPTED  = "accepted"
    REJECTED  = "rejected"
    CANCELLED = "cancelled"
    EXPIRED   = "expired"
    OUTBID    = "outbid"


class AnnouncementWaypointType(enum.Enum):
    ORIGIN      = "origin"       # Jo'nab ketish nuqtasi
    DESTINATION = "destination"  # Yetib borish nuqtasi
    TRANSIT     = "transit"      # Oraliq to'xtash


class AnnouncementStatus(enum.Enum):
    ACTIVE    = "active"
    FILLED    = "filled"     # Yuk topildi, band
    EXPIRED   = "expired"    # Muddati o'tdi
    CANCELLED = "cancelled"  # Haydovchi bekor qildi


class DriverVerificationStatus(enum.Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ═══════════════════════════════════════════════
# TRUCK TYPE — Yuk mashinasi turi
# ═══════════════════════════════════════════════

class TruckType(Base):
    __tablename__ = "truck_types"

    id   : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name : Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # O'lcham va sig'im
    max_weight      : Mapped[float]      = mapped_column(Numeric(6, 2), nullable=False)   # tonna
    max_volume      : Mapped[float]      = mapped_column(Numeric(6, 2), nullable=False)   # m³
    length          : Mapped[float|None] = mapped_column(Numeric(5, 2), nullable=True)    # m
    width           : Mapped[float|None] = mapped_column(Numeric(5, 2), nullable=True)    # m
    height          : Mapped[float|None] = mapped_column(Numeric(5, 2), nullable=True)    # m
    pallet_capacity : Mapped[int|None]   = mapped_column(Integer,       nullable=True)

    # Meta
    image_url   : Mapped[str|None]  = mapped_column(String(512), nullable=True)   # ikonka / rasm
    description : Mapped[str|None]  = mapped_column(String(200), nullable=True)
    is_active   : Mapped[bool]      = mapped_column(Boolean, default=True)
    created_at  : Mapped[datetime]  = mapped_column(DateTime, default=func.now())

    # Relationships
    drivers : Mapped[list["Driver"]] = relationship("Driver", back_populates="truck_type_obj")

    def __repr__(self) -> str:
        return f"<TruckType(id={self.id}, name='{self.name}')>"


# ═══════════════════════════════════════════════
# DRIVER — Haydovchi
# ═══════════════════════════════════════════════

class Driver(Base):
    __tablename__ = "drivers"

    id      : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id : Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)

    truck_type_id  : Mapped[int]     = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=False)
    truck_number   : Mapped[str]     = mapped_column(String(20), unique=True, nullable=False)
    truck_year     : Mapped[int|None]= mapped_column(SmallInteger, nullable=True)

    current_city   : Mapped[str|None]     = mapped_column(String(300))
    current_region : Mapped[str|None]= mapped_column(String(100))

    # Real-time GPS
    is_live_location_active  : Mapped[bool]         = mapped_column(Boolean,  default=False)
    live_location_expires    : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
    last_latitude            : Mapped[float|None]    = mapped_column(Float,    nullable=True)
    last_longitude           : Mapped[float|None]    = mapped_column(Float,    nullable=True)
    last_location_at         : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    # Statistika
    rating          : Mapped[float] = mapped_column(Numeric(3, 2), default=5.0)
    total_trips     : Mapped[int]   = mapped_column(Integer, default=0)
    cancel_count    : Mapped[int]   = mapped_column(Integer, default=0)
    on_time_percent : Mapped[float] = mapped_column(Numeric(5, 2), default=100.0)

    # Holat
    is_available  : Mapped[bool] = mapped_column(Boolean, default=True)
    docs_verified : Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked    : Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason  : Mapped[str|None] = mapped_column(String(300), nullable=True)

    created_at : Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at : Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────
    user           = relationship("User", back_populates="driver")
    truck_type_obj : Mapped["TruckType"]              = relationship("TruckType", back_populates="drivers")
    documents      : Mapped[list["DriverDocument"]]   = relationship("DriverDocument",   back_populates="driver", cascade="all, delete-orphan")
    announcements  : Mapped[list["DriverAnnouncement"]] = relationship("DriverAnnouncement", back_populates="driver")
    offers         : Mapped[list["OrderOffer"]]        = relationship("OrderOffer",      back_populates="driver")

    # AI
    chats            : Mapped[list["Chat"]]   = relationship(back_populates="driver", lazy="select")
    ratings_given    : Mapped[list["Rating"]] = relationship(
                            foreign_keys="[Rating.rated_by_driver]",
                            back_populates="rater_driver",      lazy="select")
    ratings_received : Mapped[list["Rating"]] = relationship(
                            foreign_keys="[Rating.target_driver]",
                            back_populates="target_driver_obj", lazy="select")

    # ── Helper property lar ───────────────────────

    @property
    def is_gps_live(self) -> bool:
        """GPS hozir aktiv va muddati o'tmagan"""
        if not self.is_live_location_active:
            return False
        if self.live_location_expires and datetime.now(timezone.utc) > self.live_location_expires:
            return False
        return True

    @property
    def reliability_score(self) -> float:
        """
        Ishonchlilik ko'rsatkichi (0–100):
        reyting × 14 + on_time_percent × 0.4 + (trip bonusi, max 20)
        """
        trip_bonus = min(self.total_trips / 5, 20)
        return round(
            float(self.rating or 0) * 14
            + float(self.on_time_percent or 0) * 0.4
            + trip_bonus,
            1,
        )

    def __repr__(self) -> str:
        return f"<Driver(id={self.id}, truck='{self.truck_number}', city='{self.current_city}')>"




class DocumentType(enum.Enum):
    DRIVER_LICENSE    = "driver_license"     # Haydovchilik guvohnomasi
    PASSPORT          = "passport"           # Pasport
    TRUCK_TECH_PASS   = "truck_tech_pass"    # Texnik pasport
    TRUCK_INSURANCE   = "truck_insurance"    # Sug'urta
    MEDICAL_CERT      = "medical_cert"       # Tibbiy ma'lumotnoma
    OTHER             = "other"


class DriverDocument(Base):
    __tablename__ = "driver_documents"

    id          : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    driver_id   : Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False)

    doc_type    : Mapped[DocumentType] = mapped_column(SQLEnum(DocumentType), nullable=False)
    file_url    : Mapped[str]          = mapped_column(String(512), nullable=False)   # S3 URL
    file_name   : Mapped[str|None]     = mapped_column(String(255), nullable=True)

    # Amal qilish muddati
    expires_at  : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
    is_expired  : Mapped[bool]          = mapped_column(Boolean,  default=False)

    # Admin tekshiruvi
    verification_status : Mapped[DriverVerificationStatus] = mapped_column(
        SQLEnum(DriverVerificationStatus),
        default=DriverVerificationStatus.PENDING,
        nullable=False,
    )
    rejection_reason    : Mapped[str|None] = mapped_column(String(300), nullable=True)
    verified_by         : Mapped[int|None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    verified_at         : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    created_at  : Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    driver : Mapped["Driver"] = relationship("Driver", back_populates="documents")

    @property
    def is_valid(self) -> bool:
        return (
            self.verification_status == DriverVerificationStatus.APPROVED
            and not self.is_expired
        )

    def __repr__(self) -> str:
        return f"<DriverDocument(driver={self.driver_id}, type={self.doc_type.value}, status={self.verification_status.value})>"


# ═══════════════════════════════════════════════
# DRIVER ANNOUNCEMENT — Haydovchi e'loni
# "Toshkentdan Samarqandga boraman, yuk bor?"
# ═══════════════════════════════════════════════

class DriverAnnouncement(Base):
    __tablename__ = "driver_announcements"

    id        : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    driver_id : Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id"), nullable=False, index=True)

    # Umumiy masofa (waypointlar bo'yicha hisoblanadi)
    total_distance_km : Mapped[float|None] = mapped_column(Numeric(8, 2), nullable=True)

    # Narx
    price    : Mapped[float]     = mapped_column(Numeric(12, 2), nullable=False)
    currency : Mapped[str]       = mapped_column(String(10),     default="UZS")

    # Sig'im (o'sha safar uchun qolgan bo'sh joy)
    available_weight : Mapped[float|None] = mapped_column(Numeric(6, 2), nullable=True)  # tonna
    available_volume : Mapped[float|None] = mapped_column(Numeric(6, 2), nullable=True)  # m³

    # Jo'nash vaqti
    departure_date   : Mapped[datetime]      = mapped_column(DateTime, nullable=False)
    arrival_date     : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    # Taklif qabul qilish muddati
    expires_at       : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    description : Mapped[str|None] = mapped_column(String(500), nullable=True)

    status : Mapped[AnnouncementStatus] = mapped_column(
        SQLEnum(AnnouncementStatus), default=AnnouncementStatus.ACTIVE, nullable=False, index=True
    )

    created_at : Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at : Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    driver     : Mapped["Driver"]                      = relationship("Driver", back_populates="announcements")
    waypoints  : Mapped[list["AnnouncementWaypoint"]]  = relationship(
                        "AnnouncementWaypoint",
                        back_populates="announcement",
                        order_by="AnnouncementWaypoint.sequence",
                        cascade="all, delete-orphan",
                    )
    offers     : Mapped[list["AnnouncementOffer"]]     = relationship("AnnouncementOffer", back_populates="announcement")

    # ── Helper property lar ───────────────────────

    @property
    def origin(self) -> "AnnouncementWaypoint | None":
        return self.waypoints[0] if self.waypoints else None

    @property
    def destination(self) -> "AnnouncementWaypoint | None":
        return self.waypoints[-1] if self.waypoints else None

    @property
    def transit_stops(self) -> list["AnnouncementWaypoint"]:
        return self.waypoints[1:-1] if len(self.waypoints) > 2 else []

    @property
    def is_active(self) -> bool:
        if self.status != AnnouncementStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def __repr__(self) -> str:
        stops = len(self.waypoints) if self.waypoints else 0
        return f"<Announcement(id={self.id}, driver={self.driver_id}, stops={stops}, status={self.status.value})>"


# ═══════════════════════════════════════════════
# ANNOUNCEMENT WAYPOINT — E'lon marshrutining har bir nuqtasi
# ═══════════════════════════════════════════════

class AnnouncementWaypoint(Base):
    __tablename__ = "announcement_waypoints"

    id              : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id : Mapped[int] = mapped_column(
                            Integer, ForeignKey("driver_announcements.id", ondelete="CASCADE"),
                            nullable=False, index=True,
                        )

    sequence      : Mapped[int]            = mapped_column(SmallInteger, nullable=False)
    waypoint_type : Mapped[AnnouncementWaypointType] = mapped_column(
                        SQLEnum(AnnouncementWaypointType), nullable=False
                    )

    # Manzil
    city      : Mapped[str]      = mapped_column(String(100), nullable=False, index=True)
    region    : Mapped[str|None] = mapped_column(String(100), nullable=True)
    address   : Mapped[str|None] = mapped_column(String(300), nullable=True)

    # GPS
    latitude  : Mapped[float|None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude : Mapped[float|None] = mapped_column(Numeric(10, 7), nullable=True)

    # Oldingi nuqtadan masofа
    distance_from_prev_km : Mapped[float|None] = mapped_column(Numeric(8, 2), nullable=True)

    # Bu nuqtada qancha vaqt to'xtaydi (daqiqalarda)
    stop_duration_min : Mapped[int|None] = mapped_column(SmallInteger, nullable=True)

    # Rejalashtirilgan vaqt
    scheduled_at : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    # Izoh
    note : Mapped[str|None] = mapped_column(Text, nullable=True)

    created_at : Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    announcement : Mapped["DriverAnnouncement"] = relationship("DriverAnnouncement", back_populates="waypoints")

    def __repr__(self) -> str:
        return (
            f"<AnnWaypoint(ann={self.announcement_id}, seq={self.sequence}, "
            f"city='{self.city}', type={self.waypoint_type.value})>"
        )


# ═══════════════════════════════════════════════
# ANNOUNCEMENT OFFER — Mijozning e'longa taklifi
# ═══════════════════════════════════════════════

class AnnouncementOffer(Base):
    __tablename__ = "announcement_offers"

    id              : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id : Mapped[int] = mapped_column(Integer, ForeignKey("driver_announcements.id"), nullable=False, index=True)
    customer_id     : Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)

    # Yuk ma'lumotlari
    cargo_name        : Mapped[str]        = mapped_column(String(200),   nullable=False)
    cargo_description : Mapped[str|None]   = mapped_column(String(500),   nullable=True)
    cargo_weight      : Mapped[float|None] = mapped_column(Numeric(6, 2), nullable=True)   # tonna
    cargo_volume      : Mapped[float|None] = mapped_column(Numeric(6, 2), nullable=True)   # m³

    # Qaysi nuqtadan qaysi nuqtaga (e'lon marshruti ichidan)
    pickup_city   : Mapped[str|None] = mapped_column(String(100), nullable=True)
    delivery_city : Mapped[str|None] = mapped_column(String(100), nullable=True)

    # Narx muzakarasi
    offered_price   : Mapped[float]       = mapped_column(Numeric(12, 2), nullable=False)
    currency        : Mapped[str]         = mapped_column(String(10),     default="UZS")
    counter_price   : Mapped[float|None]  = mapped_column(Numeric(12, 2), nullable=True)
    counter_comment : Mapped[str|None]    = mapped_column(String(500),    nullable=True)
    counter_at      : Mapped[datetime|None] = mapped_column(DateTime,     nullable=True)

    comment : Mapped[str|None] = mapped_column(String(500), nullable=True)

    # Ko'rindi / ko'rilmadi
    is_seen : Mapped[bool]          = mapped_column(Boolean,  default=False)
    seen_at : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    # Taklif muddati
    expires_at : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    status : Mapped[AnnouncementOfferStatus] = mapped_column(
        SQLEnum(AnnouncementOfferStatus),
        default=AnnouncementOfferStatus.PENDING,
        nullable=False,
        index=True,
    )
    status_reason : Mapped[str|None] = mapped_column(String(300), nullable=True)

    # Timestamps
    created_at   : Mapped[datetime]        = mapped_column(DateTime, default=func.now())
    updated_at   : Mapped[datetime]        = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    accepted_at  : Mapped[datetime|None]   = mapped_column(DateTime, nullable=True)
    cancelled_at : Mapped[datetime|None]   = mapped_column(DateTime, nullable=True)

    # Relationships
    announcement : Mapped["DriverAnnouncement"] = relationship("DriverAnnouncement", back_populates="offers")
    customer                                    = relationship("User")

    # ── Helper property lar ───────────────────────

    @property
    def final_price(self) -> float:
        return float(self.counter_price or self.offered_price)

    @property
    def is_active(self) -> bool:
        if self.status not in (AnnouncementOfferStatus.PENDING, AnnouncementOfferStatus.SEEN):
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    def mark_seen(self) -> None:
        self.is_seen = True
        self.seen_at = datetime.now(timezone.utc)
        if self.status == AnnouncementOfferStatus.PENDING:
            self.status = AnnouncementOfferStatus.SEEN

    def accept(self) -> None:
        self.status = AnnouncementOfferStatus.ACCEPTED
        self.accepted_at = datetime.now(timezone.utc)

    def reject(self, reason: str | None = None) -> None:
        self.status = AnnouncementOfferStatus.REJECTED
        self.status_reason = reason

    def cancel(self, reason: str | None = None) -> None:
        self.status = AnnouncementOfferStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)
        self.status_reason = reason

    def __repr__(self) -> str:
        return (
            f"<AnnOffer(id={self.id}, ann={self.announcement_id}, "
            f"customer={self.customer_id}, price={self.offered_price}, "
            f"status={self.status.value})>"
        )