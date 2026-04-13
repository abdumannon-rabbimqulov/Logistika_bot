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

    model_config = ConfigDict(from_attributes=True)