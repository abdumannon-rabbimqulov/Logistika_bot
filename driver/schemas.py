from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from enum import Enum


class AnnouncementOfferStatus(str, Enum):
    PENDING   = "PENDING"
    SEEN      = "SEEN"
    ACCEPTED  = "ACCEPTED"
    REJECTED  = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED   = "EXPIRED"
    OUTBID    = "OUTBID"

class AnnouncementWaypointType(str, Enum):
    ORIGIN      = "ORIGIN"
    DESTINATION = "DESTINATION"
    TRANSIT     = "TRANSIT"

class AnnouncementStatus(str, Enum):
    ACTIVE    = "ACTIVE"
    FILLED    = "FILLED"
    EXPIRED   = "EXPIRED"
    CANCELLED = "CANCELLED"

class DriverVerificationStatus(str, Enum):
    PENDING  = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class DocumentType(str, Enum):
    DRIVER_LICENSE    = "DRIVER_LICENSE"
    PASSPORT          = "PASSPORT"
    TRUCK_TECH_PASS   = "TRUCK_TECH_PASS"
    TRUCK_INSURANCE   = "TRUCK_INSURANCE"
    MEDICAL_CERT      = "MEDICAL_CERT"
    OTHER             = "OTHER"


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


class DriverBase(BaseModel):
    truck_type_id: int = Field(..., description="Yuk mashinasi turi ID si")
    truck_number: str = Field(..., min_length=3, max_length=20, description="Davlat raqami (60A123BC)")
    truck_year: Optional[int] = Field(None, ge=1980, le=2030, description="Ishlab chiqarilgan yil")
    current_city: str = Field(..., min_length=2, max_length=100, description="Hozirgi shahar")
    current_region: Optional[str] = Field(None, max_length=100, description="Viloyat / Region")


class DriverCreate(DriverBase):
    phone_number: Optional[str] = Field(None, max_length=20, description="Aloqa raqami (User.phone_number ga yoziladi)")

    @field_validator("phone_number", mode="before")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        from utils.validation import normalize_phone_number
        return normalize_phone_number(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "truck_type_id": 2,
                "truck_number": "10Z123ZZ",
                "truck_year": 2021,
                "current_city": "Namangan",
                "current_region": "Namangan viloyati",
                "phone_number": "+998901112233",
            }
        }
    )


class DriverUpdate(BaseModel):
    truck_type_id: Optional[int] = None
    truck_number: Optional[str] = Field(None, max_length=20)
    truck_year: Optional[int] = None
    current_city: Optional[str] = None
    current_region: Optional[str] = None
    is_available: Optional[bool] = None
    is_live_location_active: Optional[bool] = None


class UserStatus(str, Enum):
    LIVE = "LIVE"
    OFFLINE = "OFFLINE"


class GpsStatus(str, Enum):
    ON = "ON"
    OFF = "OFF"


class DriverProfileResponse(BaseModel):
    """Haydovchi kabineti — ixcham profil (GET /drivers/me, /drivers/profile)."""

    id: int
    user_id: int
    name: str
    rating: float
    balance: str = Field(..., description="Formatlangan balans, masalan: 1 200 000 UZS")
    balance_amount: Decimal
    currency: str = "UZS"
    user_status: UserStatus
    gps_status: GpsStatus
    phone_number: Optional[str] = None
    truck_type_id: int
    truck_type_name: Optional[str] = None
    truck_number: str
    truck_year: Optional[int] = None
    current_city: Optional[str] = None
    current_region: Optional[str] = None
    is_available: bool
    total_trips: int
    on_time_percent: Decimal
    is_blocked: bool = False


class DriverTripScope(str, Enum):
    CURRENT = "current"
    COMPLETED = "completed"
    ALL = "all"


class DriverResponse(BaseModel):
    id: int
    user_id: int
    truck_type_id: int
    truck_number: str
    truck_year: Optional[int] = None
    current_city: Optional[str] = None
    current_region: Optional[str] = None
    rating: Decimal
    total_trips: int
    cancel_count: int
    on_time_percent: Decimal
    is_available: bool
    is_blocked: bool
    block_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DriverDocumentBase(BaseModel):
    doc_type: DocumentType = Field(...)
    file_url: str = Field(...)
    file_name: Optional[str] = Field(None)
    expires_at: Optional[datetime] = None

    @field_validator("doc_type", mode="before", check_fields=False)
    @classmethod
    def uppercase_enum_input(cls, v):
        if isinstance(v, str):
            return v.upper()
        if hasattr(v, "value"):
            return str(v.value).upper()
        return v

    @field_serializer("doc_type", check_fields=False)
    def serialize_enum_lower(self, enum_val, _info):
        if hasattr(enum_val, "value"):
            return enum_val.value.lower()
        if isinstance(enum_val, str):
            return enum_val.lower()
        return enum_val

class DriverDocumentCreate(DriverDocumentBase):
    driver_id: int = Field(...)

class DriverDocumentUpdate(BaseModel):
    verification_status: Optional[DriverVerificationStatus] = None
    rejection_reason: Optional[str] = None

    @field_validator("verification_status", mode="before", check_fields=False)
    @classmethod
    def uppercase_enum_input(cls, v):
        if isinstance(v, str):
            return v.upper()
        if hasattr(v, "value"):
            return str(v.value).upper()
        return v

class DriverDocumentResponse(DriverDocumentBase):
    id: int
    driver_id: int
    verification_status: DriverVerificationStatus
    rejection_reason: Optional[str] = None
    verified_by: Optional[int] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("verification_status", check_fields=False)
    def serialize_enum_lower(self, enum_val, _info):
        if hasattr(enum_val, "value"):
            return enum_val.value.lower()
        if isinstance(enum_val, str):
            return enum_val.lower()
        return enum_val


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

    @field_validator("waypoint_type", mode="before", check_fields=False)
    @classmethod
    def uppercase_enum_input(cls, v):
        if isinstance(v, str):
            return v.upper()
        if hasattr(v, "value"):
            return str(v.value).upper()
        return v

    @field_serializer("waypoint_type", check_fields=False)
    def serialize_enum_lower(self, enum_val, _info):
        if hasattr(enum_val, "value"):
            return enum_val.value.lower()
        if isinstance(enum_val, str):
            return enum_val.lower()
        return enum_val

class AnnouncementWaypointCreate(AnnouncementWaypointBase):
    pass

class AnnouncementWaypointResponse(AnnouncementWaypointBase):
    id: int
    announcement_id: int
    model_config = ConfigDict(from_attributes=True)


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

    @field_validator("status", mode="before", check_fields=False)
    @classmethod
    def uppercase_enum_input(cls, v):
        if isinstance(v, str):
            return v.upper()
        if hasattr(v, "value"):
            return str(v.value).upper()
        return v

    @field_serializer("status", check_fields=False)
    def serialize_enum_lower(self, enum_val, _info):
        if hasattr(enum_val, "value"):
            return enum_val.value.lower()
        if isinstance(enum_val, str):
            return enum_val.lower()
        return enum_val

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

    @field_validator("status", mode="before", check_fields=False)
    @classmethod
    def uppercase_enum_input(cls, v):
        if isinstance(v, str):
            return v.upper()
        if hasattr(v, "value"):
            return str(v.value).upper()
        return v

class DriverAnnouncementResponse(DriverAnnouncementBase):
    id: int
    driver_id: int
    total_distance_km: Optional[Decimal] = Field(None)
    created_at: datetime
    updated_at: datetime
    waypoints: List[AnnouncementWaypointResponse]
    model_config = ConfigDict(from_attributes=True)


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

    @field_validator("status", mode="before", check_fields=False)
    @classmethod
    def uppercase_enum_input(cls, v):
        if isinstance(v, str):
            return v.upper()
        if hasattr(v, "value"):
            return str(v.value).upper()
        return v

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

    @field_serializer("status", check_fields=False)
    def serialize_enum_lower(self, enum_val, _info):
        if hasattr(enum_val, "value"):
            return enum_val.value.lower()
        if isinstance(enum_val, str):
            return enum_val.lower()
        return enum_val