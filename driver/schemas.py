from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer
from datetime import datetime
from decimal import Decimal
from typing import Optional
from utils.validation import CaseInsensitiveSchemaEnum




class DriverVerificationStatus(CaseInsensitiveSchemaEnum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class DocumentType(CaseInsensitiveSchemaEnum):
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
    base_price: Decimal = Field(Decimal("0"), ge=0, description="Boshlang'ich narx, UZS")
    price_per_km: Decimal = Field(Decimal("0"), ge=0, description="1 km uchun narx, UZS")
    min_price: Optional[Decimal] = Field(None, ge=0, description="Minimal narx (pol), UZS")
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
    base_price: Optional[Decimal] = Field(None, ge=0)
    price_per_km: Optional[Decimal] = Field(None, ge=0)
    min_price: Optional[Decimal] = Field(None, ge=0)
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


class UserStatus(CaseInsensitiveSchemaEnum):
    LIVE = "LIVE"
    OFFLINE = "OFFLINE"


class GpsStatus(CaseInsensitiveSchemaEnum):
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


class DriverTripScope(CaseInsensitiveSchemaEnum):
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
