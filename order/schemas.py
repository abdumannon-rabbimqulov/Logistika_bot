from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum

# --- ENUM Schemas ---

class OrderStatus(str, Enum):
    PENDING     = "pending"
    ACCEPTED    = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    CANCELLED   = "cancelled"

class WaypointType(str, Enum):
    PICKUP   = "pickup"
    DELIVERY = "delivery"
    TRANSIT  = "transit"

class WaypointStatus(str, Enum):
    PENDING   = "pending"
    ARRIVED   = "arrived"
    COMPLETED = "completed"
    SKIPPED   = "skipped"

class OfferStatus(str, Enum):
    PENDING   = "pending"
    SEEN      = "seen"
    ACCEPTED  = "accepted"
    REJECTED  = "rejected"
    CANCELLED = "cancelled"
    EXPIRED   = "expired"
    OUTBID    = "outbid"

# --- OrderWaypoint Schemas ---

class OrderWaypointBase(BaseModel):
    sequence: int = Field(1, description="Tartib raqami")
    waypoint_type: WaypointType = Field(WaypointType.PICKUP, description="Nuqta turi")
    city: str = Field(..., max_length=100, example="Toshkent")
    address: Optional[str] = Field(None, max_length=300, example="Chilonzor 19-mavze")
    landmark: Optional[str] = Field(None, max_length=200, example="Makro supermarketi yonida")
    latitude: Optional[float] = Field(None, example=41.311081)
    longitude: Optional[float] = Field(None, example=69.240562)
    distance_from_prev_km: Optional[Decimal] = Field(None, example=0)
    scheduled_arrival: Optional[datetime] = None
    scheduled_departure: Optional[datetime] = None
    stop_duration_min: Optional[int] = Field(None, example=30)
    contact_name: Optional[str] = Field(None, max_length=150, example="Ali Valiyev")
    contact_phone: Optional[str] = Field(None, max_length=20, example="+998901234567")
    note: Optional[str] = Field(None, example="Iltimos, yetkazishdan oldin qo'ngiroq qiling")
    status: WaypointStatus = WaypointStatus.PENDING

class OrderWaypointCreate(OrderWaypointBase):
    pass

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
    cargo_name: str = Field(..., max_length=200, example="Mebellar to'plami")
    weight: Decimal = Field(..., example=2.5)
    volume: Optional[Decimal] = Field(None, example=12.0)
    required_truck_type_id: int = Field(..., example=1)
    price: Decimal = Field(..., example=1500000)
    currency: str = Field("UZS", example="UZS")
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None

class OrderCreate(OrderBase):
    customer_id: int = Field(..., example=1)
    waypoints: List[OrderWaypointCreate]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cargo_name": "Qurilish mollari (sement)",
                "weight": 20.0,
                "volume": 30.0,
                "required_truck_type_id": 2,
                "price": 4500000,
                "currency": "UZS",
                "customer_id": 1,
                "waypoints": [
                    {
                        "sequence": 1,
                        "waypoint_type": "pickup",
                        "city": "Toshkent",
                        "address": "Sergeli sanoat zonasi",
                        "contact_name": "Aziz",
                        "contact_phone": "+998901112233"
                    },
                    {
                        "sequence": 2,
                        "waypoint_type": "delivery",
                        "city": "Samarqand",
                        "address": "Shahar markazi",
                        "contact_name": "Jasur",
                        "contact_phone": "+998934445566"
                    }
                ]
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

class OrderResponse(OrderBase):
    id: int
    customer_id: int
    driver_id: Optional[int] = None
    total_distance_km: Optional[Decimal] = Field(None, example=320)
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    waypoints: List[OrderWaypointResponse]
    model_config = ConfigDict(from_attributes=True)

# --- OrderOffer Schemas ---

class OrderOfferBase(BaseModel):
    offered_price: Decimal = Field(..., example=1400000)
    currency: str = "UZS"
    estimated_pickup_time: Optional[datetime] = None
    estimated_delivery_time: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    driver_latitude: Optional[float] = Field(None, example=41.3)
    driver_longitude: Optional[float] = Field(None, example=69.2)
    distance_to_pickup_km: Optional[Decimal] = Field(None, example=15.5)
    truck_id: Optional[int] = Field(None, example=5)
    comment: Optional[str] = Field(None, max_length=500, example="Men 1 soatda boraman, narxi mos kelsa")

class OrderOfferCreate(OrderOfferBase):
    order_id: int = Field(..., example=10)
    driver_id: int = Field(..., example=2)

class OrderOfferUpdate(BaseModel):
    counter_price: Optional[Decimal] = None
    counter_comment: Optional[str] = None
    status: Optional[OfferStatus] = None

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
