from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from order.models import OrderStatus, WaypointStatus, WaypointType



class OrderWaypointBase(BaseModel):
    sequence: int = Field(..., ge=1, description="Nuqta tartibi: 1 - pickup, oxirgisi - delivery")
    type: WaypointType
    address: Optional[str] = Field(None, max_length=300)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    contact_name: Optional[str] = Field(None, max_length=150)
    contact_phone: Optional[str] = Field(None, max_length=20)


class OrderWaypointCreate(OrderWaypointBase):
    """Buyurtma yaratishda kelayotgan waypoint (status kiritilmaydi, default PENDING).

    Ikkala holat ham qabul qilinadi:
    - faqat `address` (matn) — backend Yandex Geocoder orqali koordinatani topadi;
    - faqat `latitude`/`longitude` (masalan Telegram "joylashuvni yuborish") — backend
      manzil matnini reverse-geocoding orqali topadi.
    Ikkalasi ham berilishi mumkin — bu holda berilgan qiymatlar ustuvor, qidiruv qilinmaydi.
    """

    @model_validator(mode="after")
    def check_address_or_coordinates(self) -> "OrderWaypointCreate":
        has_coords = self.latitude is not None and self.longitude is not None
        has_address = bool(self.address and self.address.strip())
        if not has_coords and not has_address:
            raise ValueError(
                "Har bir nuqta uchun manzil matni yoki koordinata (latitude+longitude) kiritilishi shart"
            )
        return self


class OrderWaypointUpdate(BaseModel):
    """Waypoint holatini yangilash (masalan, haydovchi nuqtaga yetganda)"""
    status: Optional[WaypointStatus] = None
    address: Optional[str] = Field(None, max_length=300)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    contact_name: Optional[str] = Field(None, max_length=150)
    contact_phone: Optional[str] = Field(None, max_length=20)


class OrderWaypointResponse(OrderWaypointBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    status: WaypointStatus
    created_at: datetime


# ============================================================
#  Order sxemalari
# ============================================================

class OrderBase(BaseModel):
    cargo_name: str = Field(..., max_length=200)
    weight: Decimal = Field(..., gt=0, description="Yuk og'irligi, tonna")
    volume: Optional[Decimal] = Field(None, gt=0, description="Yuk hajmi, m³")
    pickup_at: datetime
    required_truck_type_id: int
    price: Decimal = Field(..., gt=0)
    currency: str = Field(default="UZS", max_length=10)


class OrderCreate(OrderBase):
    """Yangi buyurtma yaratish uchun (mijoz tomonidan yuboriladi)"""

    waypoints: list[OrderWaypointCreate] = Field(..., min_length=2)

    @field_validator("waypoints")
    @classmethod
    def validate_waypoints(cls, waypoints: list[OrderWaypointCreate]) -> list[OrderWaypointCreate]:
        # Kamida bitta PICKUP va bitta DELIVERY nuqtasi bo'lishi shart
        types = [wp.type for wp in waypoints]
        if WaypointType.PICKUP not in types:
            raise ValueError("Kamida bitta PICKUP nuqtasi bo'lishi kerak")
        if WaypointType.DELIVERY not in types:
            raise ValueError("Kamida bitta DELIVERY nuqtasi bo'lishi kerak")

        # sequence'lar 1 dan boshlab ketma-ket bo'lishi kerak
        sequences = sorted(wp.sequence for wp in waypoints)
        if sequences != list(range(1, len(waypoints) + 1)):
            raise ValueError("waypoints.sequence 1 dan boshlab ketma-ket bo'lishi kerak")

        return waypoints


class OrderUpdate(BaseModel):
    """Buyurtmani qisman yangilash (barcha maydonlar ixtiyoriy)"""

    cargo_name: Optional[str] = Field(None, max_length=200)
    weight: Optional[Decimal] = Field(None, gt=0)
    volume: Optional[Decimal] = Field(None, gt=0)
    pickup_at: Optional[datetime] = None
    departure_at: Optional[datetime] = None
    required_truck_type_id: Optional[int] = None
    price: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, max_length=10)
    driver_id: Optional[int] = None
    status: Optional[OrderStatus] = None
    total_distance_km: Optional[Decimal] = Field(None, ge=0)


class OrderStatusUpdate(BaseModel):
    """Faqat statusni o'zgartirish uchun qisqartirilgan sxema"""
    status: OrderStatus


class OrderAssignDriver(BaseModel):
    """Haydovchini buyurtmaga biriktirish"""
    driver_id: int


class OrderResponse(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    driver_id: Optional[int] = None
    departure_at: Optional[datetime] = None
    total_distance_km: Optional[Decimal] = None
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    waypoints: list[OrderWaypointResponse] = []


class OrderListItem(BaseModel):
    """Ro'yxat (list) ko'rinishi uchun yengillashtirilgan sxema"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cargo_name: str
    weight: Decimal
    price: Decimal
    currency: str
    status: OrderStatus
    pickup_at: datetime
    driver_id: Optional[int] = None
    created_at: datetime


class OrderDetailResponse(OrderResponse):
    """To'liq batafsil ko'rinish: origin/destination alohida ajratib chiqarilgan"""

    origin: Optional[OrderWaypointResponse] = None
    destination: Optional[OrderWaypointResponse] = None
    current_waypoint: Optional[OrderWaypointResponse] = None

    @classmethod
    def from_order(cls, order) -> "OrderDetailResponse":
        """Order ORM obyektidagi property'larni (origin/destination/current_waypoint) sxemaga joylash"""
        base = cls.model_validate(order)
        base.origin = OrderWaypointResponse.model_validate(order.origin) if order.origin else None
        base.destination = OrderWaypointResponse.model_validate(order.destination) if order.destination else None
        base.current_waypoint = (
            OrderWaypointResponse.model_validate(order.current_waypoint) if order.current_waypoint else None
        )
        return base


# ============================================================
#  Manzil qidirish (Yandex Geocoder)
# ============================================================

class GeocodeSuggestion(BaseModel):
    """Manzil matni bo'yicha qidiruv natijasi (autocomplete uchun)."""
    address: str
    latitude: float
    longitude: float


class ReverseGeocodeResponse(BaseModel):
    """Koordinata bo'yicha topilgan manzil (sender o'z joylashuvini yuborganda)."""
    address: Optional[str] = None
    latitude: float
    longitude: float