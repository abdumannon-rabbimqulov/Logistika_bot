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
    name: str = Field(..., max_length=50, example="Fura (Tent)")
    max_weight: Decimal = Field(..., example=22.0)
    max_volume: Decimal = Field(..., example=92.0)
    length: Optional[Decimal] = Field(None, example=13.6)
    width: Optional[Decimal] = Field(None, example=2.45)
    height: Optional[Decimal] = Field(None, example=2.7)
    pallet_capacity: Optional[int] = Field(None, example=33)
    image_url: Optional[str] = Field(None, max_length=512, example="/static/uploads/truck_tent.jpg")
    description: Optional[str] = Field(None, max_length=200, example="Standart tentli fura, barcha turdagi yuklar uchun")
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
    truck_brand: Optional[str]=None
    truck_year: Optional[int] = Field(None, example=2022)
    capacity_ton: Optional[Decimal] = Field(None, example=20.0)
    capacity_m3: Optional[Decimal] = Field(None, example=86.0)
    current_city: str = Field(..., max_length=300, example="Toshkent")
    current_region: Optional[str] = Field(None, max_length=100, example="Toshkent shahri")
    is_available: bool = True

class DriverCreate(DriverBase):
    user_id: int = Field(..., example=123)

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
    rating: Decimal = Field(..., example=4.9)
    total_trips: int = Field(..., example=150)
    total_km: Decimal = Field(..., example=25400.5)
    docs_verified: bool
    is_blocked: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- DriverDocument Schemas ---

class DriverDocumentBase(BaseModel):
    doc_type: DocumentType = Field(..., example=DocumentType.DRIVER_LICENSE)
    file_url: str = Field(..., max_length=512, example="/static/uploads/docs/license_123.jpg")
    file_name: Optional[str] = Field(None, max_length=255, example="guvohnoma.jpg")
    expires_at: Optional[datetime] = None

class DriverDocumentCreate(DriverDocumentBase):
    driver_id: int = Field(..., example=10)

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
    sequence: int = Field(1, example=1)
    waypoint_type: AnnouncementWaypointType = Field(AnnouncementWaypointType.ORIGIN)
    city: str = Field(..., max_length=100, example="Buxoro")
    region: Optional[str] = Field(None, max_length=100, example="Buxoro viloyati")
    address: Optional[str] = Field(None, max_length=300, example="Markaziy dehqon bozori")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_from_prev_km: Optional[Decimal] = None
    stop_duration_min: Optional[int] = Field(None, example=60)
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
    price: Decimal = Field(..., example=2500000)
    currency: str = Field("UZS", max_length=10)
    available_weight: Optional[Decimal] = Field(None, example=10.5)
    available_volume: Optional[Decimal] = Field(None, example=40.0)
    departure_date: datetime
    arrival_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=500, example="Toshkentga bo'sh qaytyapman, arzonroq olib ketaman")
    status: AnnouncementStatus = AnnouncementStatus.ACTIVE

class DriverAnnouncementCreate(DriverAnnouncementBase):
    driver_id: int = Field(..., example=5)
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
    total_distance_km: Optional[Decimal] = Field(None, example=1050)
    created_at: datetime
    updated_at: datetime
    waypoints: List[AnnouncementWaypointResponse]
    model_config = ConfigDict(from_attributes=True)

# --- AnnouncementOffer Schemas ---

class AnnouncementOfferBase(BaseModel):
    cargo_name: str = Field(..., max_length=200, example="Maishiy texnika")
    cargo_description: Optional[str] = Field(None, max_length=500, example="Xolodilnik va televizorlar")
    cargo_weight: Optional[Decimal] = Field(None, example=1.2)
    cargo_volume: Optional[Decimal] = Field(None, example=5.0)
    pickup_city: Optional[str] = Field(None, max_length=100, example="Urganch")
    delivery_city: Optional[str] = Field(None, max_length=100, example="Toshkent")
    offered_price: Decimal = Field(..., example=800000)
    currency: str = "UZS"
    comment: Optional[str] = Field(None, max_length=500, example="Yukni 2-mayda yuklash kerak")

class AnnouncementOfferCreate(AnnouncementOfferBase):
    announcement_id: int = Field(..., example=101)
    customer_id: int = Field(..., example=50)

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