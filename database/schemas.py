from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class UserSchema(BaseModel):
    id: int
    username: Optional[str] = None
    full_name: str
    language: str = "uz"
    role: str = "guest"
    is_active: bool = True
    
    model_config = ConfigDict(from_attributes=True)

class VehicleCreateSchema(BaseModel):
    user_id: int
    model: str
    number: str
    type: str
    weight: float
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    car_photo: Optional[str] = None
    license_photo: Optional[str] = None

class OrderCreateSchema(BaseModel):
    customer_id: int
    cargo_type: str
    from_address: str
    to_address: str
    weight: float
    price: float
