import enum
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Integer, String, Boolean,
    Numeric, Float, DateTime, ForeignKey, Enum as SQLEnum
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
    truck_type_obj: Mapped["TruckType"] = relationship("TruckType", back_populates="drivers")
    announcements: Mapped[list["DriverAnnouncement"]] = relationship("DriverAnnouncement", back_populates="driver")

    def __repr__(self) -> str:
        return f"<Driver(id={self.id}, truck_number='{self.truck_number}', type='{self.truck_type}')>"




class OrderStatus(enum.Enum):
    PENDING = "pending"  # Haydovchi qidirilmoqda
    ACCEPTED = "accepted"  # Haydovchi qabul qildi
    IN_PROGRESS = "in_progress"  # Yuk yo'lda
    COMPLETED = "completed"  # Yuk yetkazildi
    CANCELLED = "cancelled"  # Bekor qilindi


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Yuk beruvchi (Customer)
    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    # Qabul qilgan haydovchi (Boshida bo'sh bo'lishi mumkin)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id"), nullable=True)

    # Yuk ma'lumotlari
    cargo_name: Mapped[str] = mapped_column(String(200), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)  # Tonnalarda
    volume: Mapped[float] = mapped_column(Numeric(6, 2), nullable=True)  # m3 larda

    # Marshrut
    from_city: Mapped[str] = mapped_column(String(), nullable=False, index=True)
    to_city: Mapped[str] = mapped_column(String(), nullable=False, index=True)
    distance_km: Mapped[float] = mapped_column(Numeric(7, 2), nullable=True)

    # Kerakli mashina turi (Dinamik TruckType jadvaliga bog'lanadi)
    required_truck_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=False)

    # Moliyaviy qism
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)  # Kelishilgan narx
    currency: Mapped[str] = mapped_column(String(10), default="UZS")

    # Muddatlar
    pickup_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # Yukni olish vaqti
    delivery_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # Yetkazish vaqti

    # Status
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )

    # Vaqtlar
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))

    # Relationship-lar
    customer = relationship("User", foreign_keys=[customer_id], backref="customer_orders")
    driver = relationship("Driver", foreign_keys=[driver_id], backref="driver_orders")
    truck_type = relationship("TruckType")

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, cargo='{self.cargo_name}', status={self.status})>"



class OfferStatus(enum.Enum):
    PENDING = "pending"  # Mijoz javobini kutmoqda
    ACCEPTED = "accepted"  # Mijozga ma'qul keldi
    REJECTED = "rejected"  # Mijoz rad etdi
    CANCELLED = "cancelled"  # Haydovchi qaytib oldi


class OrderOffer(Base):
    __tablename__ = "order_offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id"), nullable=False)

    offered_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # Yukni qachon olib keta olishi haqida qo'shimcha ma'lumot
    estimated_arrival_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    comment: Mapped[str] = mapped_column(String(500), nullable=True)

    status: Mapped[OfferStatus] = mapped_column(
        SQLEnum(OfferStatus), default=OfferStatus.PENDING, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    order = relationship("Order", back_populates="offers")
    driver = relationship("Driver", back_populates="offers")

    def __repr__(self) -> str:
        return f"<Offer(id={self.id}, price={self.offered_price}, status={self.status})>"




class DriverAnnouncement(Base):
    __tablename__ = "driver_announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("drivers.id"), nullable=False)

    # Qayerdan qayerga boradi
    from_city: Mapped[str] = mapped_column(String(), nullable=False, index=True)
    to_city: Mapped[str] = mapped_column(String(), nullable=False, index=True)

    # Qachon yo'lga chiqadi
    departure_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    # Qo'shimcha ma'lumot (masalan: "Yarim fura joy bor" yoki "Faqat naqdga")
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    # E'lon holati
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc),
                                                 onupdate=lambda: datetime.now(timezone.utc))

    # Relationship
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

    # Qaysi e'longa taklif berilmoqda
    announcement_id: Mapped[int] = mapped_column(Integer, ForeignKey("driver_announcements.id"), nullable=False)

    customer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    cargo_description: Mapped[str] = mapped_column(String(500), nullable=False)


    offered_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    status: Mapped[AnnouncementOfferStatus] = mapped_column(
        SQLEnum(AnnouncementOfferStatus), default=AnnouncementOfferStatus.PENDING, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    announcement = relationship("DriverAnnouncement", back_populates="offers")
    customer = relationship("User")

    def __repr__(self) -> str:
        return f"<AnnOffer(id={self.id}, price={self.offered_price}, status={self.status})>"

