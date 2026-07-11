from __future__ import annotations
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Integer, String, Boolean,
    Numeric, Float, DateTime, ForeignKey,
    Enum as SQLEnum, Text, SmallInteger, func, text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.config import Base
from utils.db_types import CaseInsensitiveEnum


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




class TruckType(Base):
    __tablename__ = "truck_types"

    id   : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name : Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    max_weight      : Mapped[float]      = mapped_column(Numeric(6, 2), nullable=False)   # tonna
    max_volume      : Mapped[float]      = mapped_column(Numeric(6, 2), nullable=False)   # m³
    length          : Mapped[float|None] = mapped_column(Numeric(5, 2), nullable=True)    # m
    width           : Mapped[float|None] = mapped_column(Numeric(5, 2), nullable=True)    # m
    height          : Mapped[float|None] = mapped_column(Numeric(5, 2), nullable=True)    # m
    pallet_capacity : Mapped[int|None]   = mapped_column(Integer,       nullable=True)


    image_url   : Mapped[str|None]  = mapped_column(String(512), nullable=True)   # ikonka / rasm
    description : Mapped[str|None]  = mapped_column(String(200), nullable=True)
    is_active   : Mapped[bool]      = mapped_column(Boolean, default=True)
    created_at  : Mapped[datetime]  = mapped_column(DateTime, default=func.now())

    drivers : Mapped[list["Driver"]] = relationship("Driver", back_populates="truck_type_obj")

    def __repr__(self) -> str:
        return f"<TruckType(id={self.id}, name='{self.name}')>"



class Driver(Base):
    __tablename__ = "drivers"

    id      : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id : Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)

    truck_type_id  : Mapped[int]     = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=False)
    truck_number   : Mapped[str]     = mapped_column(String(20), unique=True, nullable=False)
    truck_year     : Mapped[int|None]= mapped_column(SmallInteger, nullable=True)

    current_city   : Mapped[str|None]     = mapped_column(String(300))
    current_region : Mapped[str|None]= mapped_column(String(100))

    is_live_location_active  : Mapped[bool]         = mapped_column(Boolean,  default=False)
    live_location_expires    : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
    last_latitude            : Mapped[float|None]    = mapped_column(Float,    nullable=True)
    last_longitude           : Mapped[float|None]    = mapped_column(Float,    nullable=True)
    last_location_at         : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    rating          : Mapped[float] = mapped_column(Numeric(3, 2), default=5.0)
    total_trips     : Mapped[int]   = mapped_column(Integer, default=0)
    cancel_count    : Mapped[int]   = mapped_column(Integer, default=0)
    total_km: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    on_time_percent : Mapped[float] = mapped_column(Numeric(5, 2), default=100.0)

    is_available  : Mapped[bool] = mapped_column(Boolean, default=True)
    docs_verified : Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )
    is_blocked    : Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason  : Mapped[str|None] = mapped_column(String(300), nullable=True)

    created_at : Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at : Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    user           = relationship("User", back_populates="driver")
    truck_type_obj : Mapped["TruckType"]              = relationship("TruckType", back_populates="drivers")
    announcements  : Mapped[list["DriverAnnouncement"]] = relationship("DriverAnnouncement", back_populates="driver")



    @property
    def is_gps_live(self) -> bool:
        """GPS hozir aktiv va muddati o'tmagan"""
        if not self.is_live_location_active:
            return False
        if self.live_location_expires:
            from services.datetime_utils import to_utc_naive, utc_now_naive

            if utc_now_naive() > to_utc_naive(self.live_location_expires):
                return False
        return True

    @property
    def reliability_score(self) -> float:

        trip_bonus = min(self.total_trips / 5, 20)
        return round(
            float(self.rating or 0) * 14
            + float(self.on_time_percent or 0) * 0.4
            + trip_bonus,
            1,
        )

    def __repr__(self) -> str:
        _id = self.__dict__.get("id", "Unknown")
        _truck = self.__dict__.get("truck_number", "Unknown")
        return f"<Driver(id={_id}, truck='{_truck}')>"








class DriverAnnouncement(Base):
    __tablename__ = "driver_announcements"

    id        : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    driver_id : Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id"), nullable=False, index=True)

    total_distance_km : Mapped[float|None] = mapped_column(Numeric(8, 2), nullable=True)


    price    : Mapped[float]     = mapped_column(Numeric(12, 2), nullable=False)
    currency : Mapped[str]       = mapped_column(String(10),     default="UZS")

    available_weight : Mapped[float|None] = mapped_column(Numeric(6, 2), nullable=True)  # tonna
    available_volume : Mapped[float|None] = mapped_column(Numeric(6, 2), nullable=True)  # m³


    departure_date   : Mapped[datetime]      = mapped_column(DateTime, nullable=False)
    arrival_date     : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    expires_at       : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    description : Mapped[str|None] = mapped_column(String(500), nullable=True)

    status : Mapped[AnnouncementStatus] = mapped_column(
        CaseInsensitiveEnum(AnnouncementStatus), default=AnnouncementStatus.ACTIVE, nullable=False, index=True
    )

    created_at : Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at : Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    driver     : Mapped["Driver"]                      = relationship("Driver", back_populates="announcements")
    waypoints  : Mapped[list["AnnouncementWaypoint"]]  = relationship(
                        "AnnouncementWaypoint",
                        back_populates="announcement",
                        order_by="AnnouncementWaypoint.sequence",
                        cascade="all, delete-orphan",
                    )


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




class AnnouncementWaypoint(Base):
    __tablename__ = "announcement_waypoints"

    id              : Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    announcement_id : Mapped[int] = mapped_column(
                            Integer, ForeignKey("driver_announcements.id", ondelete="CASCADE"),
                            nullable=False, index=True,
                        )

    sequence      : Mapped[int]            = mapped_column(SmallInteger, nullable=False)
    waypoint_type : Mapped[AnnouncementWaypointType] = mapped_column(
                        CaseInsensitiveEnum(AnnouncementWaypointType), nullable=False
                    )


    city      : Mapped[str]      = mapped_column(String(100), nullable=False, index=True)
    region    : Mapped[str|None] = mapped_column(String(100), nullable=True)
    address   : Mapped[str|None] = mapped_column(String(300), nullable=True)

    # GPS
    latitude  : Mapped[float|None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude : Mapped[float|None] = mapped_column(Numeric(10, 7), nullable=True)

    distance_from_prev_km : Mapped[float|None] = mapped_column(Numeric(8, 2), nullable=True)

    stop_duration_min : Mapped[int|None] = mapped_column(SmallInteger, nullable=True)

    scheduled_at : Mapped[datetime|None] = mapped_column(DateTime, nullable=True)


    note : Mapped[str|None] = mapped_column(Text, nullable=True)

    created_at : Mapped[datetime] = mapped_column(DateTime, default=func.now())


    announcement : Mapped["DriverAnnouncement"] = relationship("DriverAnnouncement", back_populates="waypoints")

    def __repr__(self) -> str:
        return (
            f"<AnnWaypoint(ann={self.announcement_id}, seq={self.sequence}, "
            f"city='{self.city}', type={self.waypoint_type.value})>"
        )



