from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum

# --- ENUM Schemas ---

class AnnouncementOfferStatus(str, Enum):
    PENDING   = "pending"
    SEEN      = "seen"
    ACCEPTED  = "accepted"
    REJECTED  = "rejected"
    CANCELLED = "cancelled"
    EXPIRED   = "expired"
    OUTBID    = "outbid"

class AnnouncementWaypointType(str, Enum):
    ORIGIN      = "origin"
    DESTINATION = "destination"
    TRANSIT     = "transit"

class AnnouncementStatus(str, Enum):
    ACTIVE    = "active"
    FILLED    = "filled"
    EXPIRED   = "expired"
    CANCELLED = "cancelled"

class DriverVerificationStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class DocumentType(str, Enum):
    DRIVER_LICENSE    = "driver_license"
    PASSPORT          = "passport"
    TRUCK_TECH_PASS   = "truck_tech_pass"
    TRUCK_INSURANCE   = "truck_insurance"
    MEDICAL_CERT      = "medical_cert"
    OTHER             = "other"

# --- TruckType Schemas ---

class TruckTypeBase(BaseModel):
    name: str = Field()
    max_weight: Decimal
    max_volume: Decimal
    length: Optional[Decimal] = Field(None)
    width: Optional[Decimal] = Field(None)
    height: Optional[Decimal] = Field(None)
    pallet_capacity: Optional[int] = Field(None)
    image_url: Optional[str] = Field(None, max_length=512)
    description: Optional[str] = Field(None, max_length=200)
    is_active: bool = True

class TruckTypeCreate(TruckTypeBase):
    pass

class TruckTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    max_weight: Optional[Decimal] = None
    max_volume: Optional[Decimal] = None
    length: Optional[Decimal] = None
    width: Optional[Decimal] = None
    height: Optional[Decimal] = None
    pallet_capacity: Optional[int] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class TruckTypeResponse(TruckTypeBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Driver Schemas ---

class DriverBase(BaseModel):
    truck_type_id: int = Field()
    truck_number: str = Field()
    truck_year: Optional[int] =None
    current_city: Optional[str] = Field(None, max_length=300)
    current_region: Optional[str] = Field(None, max_length=100)
    is_available: bool = True

class DriverCreate(DriverBase):
    user_id: int = Field()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "truck_type_id": 2,
                "truck_number": "10 Z 123 ZZ",
                "truck_brand": "Volvo FH16",
                "truck_year": 2021,
                "capacity_ton": 22.5,
                "capacity_m3": 90.0,
                "current_city": "Namangan",
                "current_region": "Namangan viloyati",
                "user_id": 123
            }
        }
    )

class DriverUpdate(BaseModel):
    truck_type_id: Optional[int] = None
    truck_number: Optional[str] = Field(None, max_length=20)
    truck_brand: Optional[str] = None
    truck_year: Optional[int] = None
    capacity_ton: Optional[Decimal] = None
    capacity_m3: Optional[Decimal] = None
    current_city: Optional[str] = None
    current_region: Optional[str] = None
    is_available: Optional[bool] = None
    is_live_location_active: Optional[bool] = None
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None

class DriverResponse(DriverBase):
    id: int
    user_id: int
    rating: Decimal = Field()
    total_trips: int = Field()
    total_km: Decimal = Field()
    docs_verified: bool
    is_blocked: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- DriverDocument Schemas ---

class DriverDocumentBase(BaseModel):
    doc_type: DocumentType = Field(...)
    file_url: str = Field(...)
    file_name: Optional[str] = Field(None)
    expires_at: Optional[datetime] = None

class DriverDocumentCreate(DriverDocumentBase):
    driver_id: int = Field(...)

class DriverDocumentUpdate(BaseModel):
    verification_status: Optional[DriverVerificationStatus] = None
    rejection_reason: Optional[str] = None

class DriverDocumentResponse(DriverDocumentBase):
    id: int
    driver_id: int
    verification_status: DriverVerificationStatus
    rejection_reason: Optional[str] = None
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- AnnouncementWaypoint Schemas ---

class AnnouncementWaypointBase(BaseModel):
    sequence: int = Field(1)
    waypoint_type: AnnouncementWaypointType = Field(AnnouncementWaypointType.ORIGIN)
    city: str = Field(...)
    region: Optional[str] = Field(None)
    address: Optional[str] = Field(None)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_from_prev_km: Optional[Decimal] = None
    stop_duration_min: Optional[int] = Field(None)
    scheduled_at: Optional[datetime] = None
    note: Optional[str] = None

class AnnouncementWaypointCreate(AnnouncementWaypointBase):
    pass

class AnnouncementWaypointResponse(AnnouncementWaypointBase):
    id: int
    announcement_id: int
    model_config = ConfigDict(from_attributes=True)

# --- DriverAnnouncement Schemas ---

class DriverAnnouncementBase(BaseModel):
    price: Decimal = Field(...)
    currency: str = Field("UZS", max_length=10)
    available_weight: Optional[Decimal] = Field(None)
    available_volume: Optional[Decimal] = Field(None)
    departure_date: datetime
    arrival_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    description: Optional[str] = Field(None)
    status: AnnouncementStatus = AnnouncementStatus.ACTIVE

class DriverAnnouncementCreate(DriverAnnouncementBase):
    driver_id: int = Field(...)
    waypoints: List[AnnouncementWaypointCreate]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "price": 3000000,
                "currency": "UZS",
                "available_weight": 20.0,
                "available_volume": 80.0,
                "departure_date": "2024-05-01T08:00:00Z",
                "description": "Katta fura, bo'sh joy bor",
                "driver_id": 5,
                "waypoints": [
                    {"sequence": 1, "waypoint_type": "origin", "city": "Xiva"},
                    {"sequence": 2, "waypoint_type": "destination", "city": "Toshkent"}
                ]
            }
        }
    )

class DriverAnnouncementUpdate(BaseModel):
    price: Optional[Decimal] = None
    currency: Optional[str] = None
    available_weight: Optional[Decimal] = None
    available_volume: Optional[Decimal] = None
    status: Optional[AnnouncementStatus] = None

class DriverAnnouncementResponse(DriverAnnouncementBase):
    id: int
    driver_id: int
    total_distance_km: Optional[Decimal] = Field(None)
    created_at: datetime
    updated_at: datetime
    waypoints: List[AnnouncementWaypointResponse]
    model_config = ConfigDict(from_attributes=True)

# --- AnnouncementOffer Schemas ---

class AnnouncementOfferBase(BaseModel):
    cargo_name: str = Field(...)
    cargo_description: Optional[str] = Field(None)
    cargo_weight: Optional[Decimal] = Field(None)
    cargo_volume: Optional[Decimal] = Field(None)
    pickup_city: Optional[str] = Field(None)
    delivery_city: Optional[str] = Field(None)
    offered_price: Decimal = Field(...)
    currency: str = "UZS"
    comment: Optional[str] = Field(None, max_length=500)

class AnnouncementOfferCreate(AnnouncementOfferBase):
    announcement_id: int = Field(...,)
    customer_id: int = Field(...)

class AnnouncementOfferUpdate(BaseModel):
    counter_price: Optional[Decimal] = None
    counter_comment: Optional[str] = None
    status: Optional[AnnouncementOfferStatus] = None

class AnnouncementOfferResponse(AnnouncementOfferBase):
    id: int
    announcement_id: int
    customer_id: int
    counter_price: Optional[Decimal] = None
    counter_comment: Optional[str] = None
    counter_at: Optional[datetime] = None
    is_seen: bool
    seen_at: Optional[datetime] = None
    status: AnnouncementOfferStatus
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)