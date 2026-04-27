from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class TruckTypeBase(BaseModel):
    name: str = Field(..., max_length=50, description="Yuk mashinasi nomi")
    max_weight: float = Field(..., gt=0, description="Maksimal vazn (tonna)")
    max_volume: float = Field(..., gt=0, description="Maksimal hajm (m3)")
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    pallet_capacity: Optional[int] = None
    description: Optional[str] = Field(None, max_length=200)


class TruckTypeCreate(TruckTypeBase):
    pass


class TruckTypeUpdate(BaseModel):
    name: Optional[str] = None
    max_weight: Optional[float] = None
    max_volume: Optional[float] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    pallet_capacity: Optional[int] = None
    description: Optional[str] = None


class TruckTypeResponse(TruckTypeBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

"""
DRIVER SCHEMAS ==========================================
"""



class DriverBase(BaseModel):
    truck_type_id: int
    truck_number: str
    capacity_ton: Optional[float] = Field(None, description="Yuk ko'tarish quvvati (tonnada)")
    capacity_m3: Optional[float] = Field(None, description="Yuk hajmi (m3)")
    current_city: str
    is_available: bool = True


class DriverCreate(DriverBase):
    user_id: int


# 3. Driver ma'lumotlarini yangilash uchun (PATCH /drivers/{id})
class DriverUpdate(BaseModel):
    truck_type_id: Optional[int] = None
    truck_number: Optional[str] = None
    capacity_ton: Optional[float] = None
    capacity_m3: Optional[float] = None
    current_city: Optional[str] = None
    is_available: Optional[bool] = None
    is_live_location_active: Optional[bool] = None
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None


# 4. API orqali qaytariladigan to'liq ma'lumot (Response)
class DriverResponse(DriverBase):
    id: int
    user_id: int
    rating: float
    total_trips: int
    docs_verified: bool

    # Location ma'lumotlari
    is_live_location_active: bool
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None
    last_location_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriverShortResponse(BaseModel):
    id: int
    truck_number: str
    rating: float
    is_available: bool
    current_city: str

    model_config = ConfigDict(from_attributes=True)