from __future__ import annotations
import enum
from config.config import Base
from sqlalchemy import Integer, ForeignKey, DateTime, func,BigInteger,String,Numeric,Enum as SQLEnum, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from datetime import datetime
from decimal import Decimal

from typing import Optional



class OrderStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"   # Rejalashtirilgan (Mijoz buyurtma berdi, haydovchi topildi, lekin yuklash vaqti kelmadi)
    PENDING = "PENDING"          # Kutilmoqda (Mijoz buyurtma berdi, haydovchi qidirilmoqda)
    ACCEPTED = "ACCEPTED"        # Qabul qilindi (Haydovchi zakazni oldi, yuklash nuqtasiga ketmoqda)
    IN_PROGRESS = "IN_PROGRESS"  # Jarayonda (Haydovchi yukni oldi va manzil sari yo'lda)
    COMPLETED = "COMPLETED"      # Yakunlandi (Yuk manziliga yetdi, buyurtma muvaffaqiyatli yopildi)
    CANCELLED = "CANCELLED"      # Bekor qilindi (Mijoz yoki haydovchi tomonidan rad etildi)



class WaypointType(str, enum.Enum):
    PICKUP = "PICKUP"            # Yuk ortish joyi (A nuqta - yuk mashinaga yuklanadigan joy)
    DELIVERY = "DELIVERY"        # Yuk tushirish joyi (B nuqta - yuk yetib borishi kerak bo'lgan oxirgi manzil)
    TRANSIT = "TRANSIT"          # Oraliq nuqta (Yo'l-yonakay boshqa joydan ham yuk olish yoki tashlash uchun)


class WaypointStatus(str, enum.Enum):
    PENDING = "PENDING"          # Kutilmoqda (Haydovchi hali bu manzilga yetib kelmadi)
    ARRIVED = "ARRIVED"          # Yetib keldi (Haydovchi nuqtaga keldi va "Kelyapman/Kutib turibman" tugmasini bosdi)
    COMPLETED = "COMPLETED"      # Bajarildi (Bu nuqtadagi yuk ortish yoki tushirish ishlari tugadi)
    SKIPPED = "SKIPPED"          # Tashlab ketildi (Zarurat bo'lmagani uchun bu nuqtaga kirmasdan o'tib ketildi)

class Order(Base):
    __tablename__ = "orders"

    id          : Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id : Mapped[int]   = mapped_column(BigInteger, ForeignKey("users.id"),       nullable=False)
    driver_id   : Mapped[int | None] = mapped_column(Integer, ForeignKey("drivers.id"),   nullable=True)

    cargo_name  : Mapped[str]   = mapped_column(String(200), nullable=False)
    weight      : Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    volume      : Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)

    pickup_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    # Haydovchi yo'lga chiqishi kerak bo'lgan vaqt (Tizim hisoblaydi, boshida bo'sh bo'ladi)
    departure_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True
    )

    total_distance_km : Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)

    required_truck_type_id : Mapped[int] = mapped_column(Integer, ForeignKey("truck_types.id"), nullable=False)

    price    : Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency : Mapped[str]   = mapped_column(String(10), default="UZS")


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
        DateTime(timezone=True),
        server_default=func.now(), nullable=False

    )
    updated_at : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(), onupdate=func.now(), nullable=False
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
            if wp.status not in [WaypointStatus.COMPLETED, WaypointStatus.SKIPPED]:
                return wp
        return None




    def __repr__(self) -> str:
        _id = self.__dict__.get("id", "Unknown")
        _status = self.__dict__.get("status", "Unknown")
        return f"<Order(id={_id}, status={_status})>"




class OrderRoutePostGIS(Base):
    __tablename__ = "order_route_postgis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False,
                                          unique=True)


    geom_route: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="LINESTRING", srid=4326), nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())





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

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="waypoints")


