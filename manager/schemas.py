"""Menejer uchun javob sxemalari — MOLIYAVIY MAYDONLARSIZ.

Bu fayldagi asosiy qoida: menejer buyurtmaning narxi, komissiyasi yoki valyutasini
KO'RMAYDI. Buni "maydonni `Optional` qilib bo'sh qoldirish" bilan emas, maydonni
umuman e'lon qilmaslik bilan ta'minlaymiz — FastAPI `response_model` da bo'lmagan
kalitni javobdan butunlay chiqarib tashlaydi, ya'ni kelajakda kimdir CRUD'da
qo'shimcha ma'lumot qaytarsa ham u menejerga sizib chiqmaydi.

`FINANCE_FIELDS` — umumiy endpointlar (`/orders/...`) javobini tozalash uchun
ro'yxat: u yerda sxema hamma rollar uchun bitta, shuning uchun menejer so'ragan
javobdan bu kalitlar `strip_finance_fields()` bilan olib tashlanadi.
`tests/test_manager_finance_isolation.py` ikkala mexanizmni ham qulflab turadi.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from order.models import OrderStatus, WaypointStatus, WaypointType

# Javoblarda menejer ko'rmasligi kerak bo'lgan kalitlar. Yangi moliyaviy maydon
# qo'shilsa SHU YERGA ham qo'shilishi shart.
FINANCE_FIELDS: frozenset[str] = frozenset(
    {
        "price",
        "base_price",
        "original_price",
        "currency",
        "billable_distance_km",
        "price_bump_requested_at",
        "price_bump_count",
        "balance",
        "commission",
        "commission_percent",
        "min_allowed_price",
        "quick_price_options",
    }
)


def strip_finance_fields(payload: Any) -> Any:
    """Rekursiv ravishda moliyaviy kalitlarni olib tashlaydi (dict/list ichida ham).

    Umumiy `/orders/...` endpointlari uchun: u yerdagi sxemalar hamma rol uchun
    bitta bo'lgani sababli javob obyekti tayyor bo'lgandan keyin tozalanadi.
    """
    if isinstance(payload, dict):
        return {
            key: strip_finance_fields(value)
            for key, value in payload.items()
            if key not in FINANCE_FIELDS
        }
    if isinstance(payload, list):
        return [strip_finance_fields(item) for item in payload]
    return payload


class ManagerOrderListItem(BaseModel):
    """Ro'yxat ko'rinishi — `order.schemas.OrderListItem` dan narx olib tashlangan."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    cargo_name: str
    weight: Decimal
    status: OrderStatus
    pickup_at: datetime
    customer_id: int
    driver_id: Optional[int] = None
    required_truck_type_id: int
    overload_warning: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ManagerWaypoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sequence: int
    type: WaypointType
    status: WaypointStatus
    address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    arrived_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ManagerOrderDetail(BaseModel):
    """Batafsil ko'rinish — marshrut va yuk ma'lumotlari, narxsiz."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    driver_id: Optional[int] = None
    cargo_name: str
    weight: Decimal
    volume: Optional[Decimal] = None
    status: OrderStatus
    required_truck_type_id: int
    pickup_at: datetime
    departure_at: Optional[datetime] = None
    total_distance_km: Optional[Decimal] = None
    dispatch_round: int = 0
    overload_warning: Optional[str] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    waypoints: list[ManagerWaypoint] = []

    @classmethod
    def from_order(cls, order) -> "ManagerOrderDetail":
        return cls.model_validate(order)


class ManagerOrderStatusUpdate(BaseModel):
    status: OrderStatus


class AvailableTruck(BaseModel):
    """Buyurtmaga biriktirish mumkin bo'lgan yuk mashinasi.

    Loyihada alohida `trucks` jadvali yo'q — mashina haydovchi profilining bir qismi
    (`drivers.truck_number`, `drivers.truck_type_id`). Shuning uchun "mashinani
    biriktirish" amalda o'sha mashinaning haydovchisini biriktirishdir; menejer
    interfeysida esa aynan mashina ko'rsatiladi.
    """

    driver_id: int
    truck_number: str
    truck_type_id: int
    truck_type_name: str
    truck_year: Optional[int] = None
    max_weight: Optional[Decimal] = None
    max_volume: Optional[Decimal] = None
    rating: Decimal
    total_trips: int
    is_available: bool
    is_blocked: bool
    verification_status: str
    current_city: Optional[str] = None
    current_region: Optional[str] = None


class AssignTruckRequest(BaseModel):
    driver_id: int = Field(..., description="Tanlangan mashinaning haydovchi ID si")


class AssignTruckResponse(BaseModel):
    order: ManagerOrderDetail
    truck: AvailableTruck
