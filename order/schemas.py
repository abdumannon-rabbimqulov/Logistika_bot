from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from enum import Enum

from order.models import OrderStatus

# --- ENUM Schemas ---

class WaypointType(str, Enum):
    PICKUP   = "PICKUP"
    DELIVERY = "DELIVERY"
    TRANSIT  = "TRANSIT"

class WaypointStatus(str, Enum):
    PENDING   = "PENDING"
    ARRIVED   = "ARRIVED"
    COMPLETED = "COMPLETED"
    SKIPPED   = "SKIPPED"

class OfferStatus(str, Enum):
    PENDING   = "PENDING"
    SEEN      = "SEEN"
    ACCEPTED  = "ACCEPTED"
    REJECTED  = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED   = "EXPIRED"
    OUTBID    = "OUTBID"

# --- OrderWaypoint Schemas ---

class OrderWaypointBase(BaseModel):
    sequence: int = Field(1, description="Tartib raqami")
    waypoint_type: WaypointType = Field(WaypointType.PICKUP, description="Nuqta turi")
    address: str = Field(..., max_length=300, description="To'liq manzil (shahar/ko'cha)")
    landmark: Optional[str] = Field(None, max_length=200, description="Mo'ljal")
    latitude: Optional[float] = Field(
        None, ge=-90, le=90, description="GPS kenglik (ixtiyoriy, xaritadan tanlangan bo'lsa)"
    )
    longitude: Optional[float] = Field(
        None, ge=-180, le=180, description="GPS uzunlik (ixtiyoriy, xaritadan tanlangan bo'lsa)"
    )
    distance_from_prev_km: Optional[Decimal] = Field(None)
    scheduled_arrival: Optional[datetime] = None
    scheduled_departure: Optional[datetime] = None
    stop_duration_min: Optional[int] = Field(None)
    contact_name: Optional[str] = Field(None, max_length=150)
    contact_phone: Optional[str] = Field(None, max_length=20)
    note: Optional[str] = Field(None)
    status: WaypointStatus = WaypointStatus.PENDING

    @field_validator("contact_phone", mode="before")
    @classmethod
    def validate_contact_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        from utils.validation import normalize_phone_number
        return normalize_phone_number(v)

    @field_validator("waypoint_type", "status", mode="before", check_fields=False)
    @classmethod
    def uppercase_enum_input(cls, v):
        if isinstance(v, str):
            return v.upper()
        if hasattr(v, "value"):
            return str(v.value).upper()
        return v

    @field_serializer("waypoint_type", "status", check_fields=False)
    def serialize_enum_lower(self, enum_val, _info):
        if hasattr(enum_val, "value"):
            return enum_val.value.lower()
        if isinstance(enum_val, str):
            return enum_val.lower()
        return enum_val


class OrderWaypointCreate(OrderWaypointBase):
    """Yangi buyurtma waypoint — address majburiy, GPS ixtiyoriy (NULL bo'lishi mumkin)."""

    sequence: int = Field(1, ge=1, description="Tartib raqami")
    address: str = Field(..., min_length=1, max_length=300, description="To'liq manzil")

    @field_validator(
        "scheduled_arrival",
        "scheduled_departure",
        mode="before",
    )
    @classmethod
    def _naive_optional_datetimes(cls, value):
        if value is None or not isinstance(value, datetime):
            return value
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value


class OrderWaypointResponse(OrderWaypointBase):
    id: int
    order_id: int
    actual_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Order Schemas ---

class OrderBase(BaseModel):
    cargo_name: str = Field(..., min_length=1, max_length=200)
    weight: Decimal = Field(..., gt=0)
    volume: Optional[Decimal] = Field(None, gt=0)
    required_truck_type_id: int = Field(..., gt=0, description="Yuk mashinasi turi (majburiy)")
    price: Decimal = Field(..., gt=0)
    currency: str = Field("UZS")
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None

class OrderCreate(OrderBase):
    waypoints: List[OrderWaypointCreate] = Field(..., min_length=2)

    @field_validator("scheduled_start", "scheduled_end", mode="before")
    @classmethod
    def _naive_optional_datetimes(cls, value):
        if value is None or not isinstance(value, datetime):
            return value
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cargo_name": "Qurilish mollari (sement)",
                "weight": 20.0,
                "volume": 30.0,
                "required_truck_type_id": 2,
                "price": 4500000,
                "currency": "UZS",
                "waypoints": [
                    {
                        "sequence": 1,
                        "waypoint_type": "pickup",
                        "address": "Toshkent, Sergeli sanoat zonasi",
                        "latitude": 41.220394,
                        "longitude": 69.350832,
                        "contact_name": "Aziz",
                        "contact_phone": "+998901112233",
                    },
                    {
                        "sequence": 2,
                        "waypoint_type": "delivery",
                        "address": "Samarqand, Shahar markazi",
                        "latitude": 39.6542,
                        "longitude": 66.9597,
                        "contact_name": "Jasur",
                        "contact_phone": "+998934445566",
                    },
                ],
            }
        }
    )

class OrderUpdate(BaseModel):
    cargo_name: Optional[str] = None
    weight: Optional[Decimal] = None
    volume: Optional[Decimal] = None
    price: Optional[Decimal] = None
    status: Optional[OrderStatus] = None
    driver_id: Optional[int] = None

    @field_validator("status", mode="before", check_fields=False)
    @classmethod
    def uppercase_enum_input(cls, v):
        if isinstance(v, str):
            return v.upper()
        if hasattr(v, "value"):
            return str(v.value).upper()
        return v

class OrderResponse(OrderBase):
    id: int
    customer_id: int
    driver_id: Optional[int] = None
    total_distance_km: Optional[Decimal] = Field(None)
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    waypoints: List[OrderWaypointResponse]
    model_config = ConfigDict(from_attributes=True)

    @field_validator("waypoints", mode="before")
    @classmethod
    def sort_waypoints_by_sequence(cls, value):
        if not value:
            return value
        if isinstance(value, list):
            return sorted(value, key=lambda w: getattr(w, "sequence", w.get("sequence", 0) if isinstance(w, dict) else 0))
        return value

    @field_serializer("status", check_fields=False)
    def serialize_enum_lower(self, enum_val, _info):
        if hasattr(enum_val, "value"):
            return enum_val.value.lower()
        if isinstance(enum_val, str):
            return enum_val.lower()
        return enum_val

# --- OrderOffer Schemas ---

class OrderOfferBase(BaseModel):
    offered_price: Decimal = Field(...)
    currency: str = "UZS"
    estimated_pickup_time: Optional[datetime] = None
    estimated_delivery_time: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    driver_latitude: Optional[float] = Field(None)
    driver_longitude: Optional[float] = Field(None)
    distance_to_pickup_km: Optional[Decimal] = Field(None)
    truck_id: Optional[int] = Field(None)
    comment: Optional[str] = Field(None, max_length=500)

class OrderOfferCreate(OrderOfferBase):
    order_id: int = Field(...)
    driver_id: int = Field(...)

class OrderOfferUpdate(BaseModel):
    counter_price: Optional[Decimal] = None
    counter_comment: Optional[str] = None
    status: Optional[OfferStatus] = None

    @field_validator("status", mode="before", check_fields=False)
    @classmethod
    def uppercase_enum_input(cls, v):
        if isinstance(v, str):
            return v.upper()
        if hasattr(v, "value"):
            return str(v.value).upper()
        return v

class OrderOfferResponse(OrderOfferBase):
    id: int
    order_id: int
    driver_id: int
    counter_price: Optional[Decimal] = None
    counter_comment: Optional[str] = None
    counter_at: Optional[datetime] = None
    is_seen: bool
    seen_at: Optional[datetime] = None
    status: OfferStatus
    status_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    accepted_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("status", check_fields=False)
    def serialize_enum_lower(self, enum_val, _info):
        if hasattr(enum_val, "value"):
            return enum_val.value.lower()
        if isinstance(enum_val, str):
            return enum_val.lower()
        return enum_val
