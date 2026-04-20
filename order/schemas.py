from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from models import OfferStatus, OrderStatus



class OrderBase(BaseModel):
    cargo_name: str = Field(..., max_length=200)
    weight: Decimal = Field(..., gt=0, max_digits=6, decimal_places=2)
    volume: Optional[Decimal] = Field(None, max_digits=6, decimal_places=2)

    from_city: str
    to_city: str
    distance_km: Optional[Decimal] = Field(None, max_digits=7, decimal_places=2)

    required_truck_type_id: int
    price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(default="UZS", max_length=10)

    pickup_date: datetime
    delivery_date: Optional[datetime] = None


class OrderCreate(OrderBase):
    pass


class OrderUpdate(BaseModel):
    cargo_name: Optional[str] = Field(None, max_length=200)
    weight: Optional[Decimal] = Field(None, gt=0, max_digits=6, decimal_places=2)
    volume: Optional[Decimal] = Field(None, max_digits=6, decimal_places=2)
    from_city: Optional[str] = None
    to_city: Optional[str] = None
    distance_km: Optional[Decimal] = Field(None, max_digits=7, decimal_places=2)
    required_truck_type_id: Optional[int] = None
    price: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    currency: Optional[str] = Field(None, max_length=10)
    pickup_date: Optional[datetime] = None
    delivery_date: Optional[datetime] = None
    status: Optional[OrderStatus] = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderRead(OrderBase):
    id: int
    customer_id: int
    driver_id: Optional[int] = None
    status: OrderStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderReadWithOffers(OrderRead):
    offers: list["OrderOfferRead"] = []

    model_config = {"from_attributes": True}



class OrderOfferBase(BaseModel):
    offered_price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2)
    estimated_arrival_time: Optional[datetime] = None
    comment: Optional[str] = Field(None, max_length=500)


class OrderOfferCreate(OrderOfferBase):
    pass


class OrderOfferUpdate(BaseModel):
    offered_price: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    estimated_arrival_time: Optional[datetime] = None
    comment: Optional[str] = Field(None, max_length=500)
    status: Optional[OfferStatus] = None


class OrderOfferStatusUpdate(BaseModel):
    status: OfferStatus


class OrderOfferRead(OrderOfferBase):
    id: int
    order_id: int
    driver_id: int
    status: OfferStatus
    created_at: datetime

    model_config = {"from_attributes": True}


OrderReadWithOffers.model_rebuild()