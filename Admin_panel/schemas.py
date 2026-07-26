
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from order.models import OrderStatus
from users.models import UserRole


# ════════════════════════════════════════════════════════════
# USERS
# ════════════════════════════════════════════════════════════


class AdminUserListItem(BaseModel):
    id: int
    username: Optional[str] = None
    full_name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    language: str
    is_active: bool
    is_banned: bool
    balance: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserList(BaseModel):
    total: int
    items: List[AdminUserListItem]


class AdminUserUpdate(BaseModel):
    """PATCH /system/users/{user_id} — qisman yangilash.

    Barcha maydonlar ixtiyoriy: so'rovda nechtasi kelsa, o'shalari yangilanadi.
    Sxemada yo'q maydonlar (masalan `balance`) jim e'tiborsiz qoldiriladi —
    admin panel ro'yxatdagi butun obyektni qaytarib yuborsa ham xato bo'lmasin.
    """

    model_config = ConfigDict(extra="ignore")

    role: Optional[UserRole] = None
    is_banned: Optional[bool] = None
    is_active: Optional[bool] = None
    language: Optional[str] = Field(None, min_length=2, max_length=10)
    full_name: Optional[str] = Field(None, min_length=1, max_length=128)

    @field_validator("role", mode="before")
    @classmethod
    def lower_role(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower()
        return v


# ════════════════════════════════════════════════════════════
# ORDERS
# ════════════════════════════════════════════════════════════


class AdminOrderUpdate(BaseModel):
    """PATCH /system/orders/{order_id} — qisman yangilash (admin moderatsiyasi).

    `status` boshqa maydonlardan farqli ravishda `order_crud.update_order_status`
    orqali qo'llaniladi (komissiya yechish va `completed_at` o'sha yerda).
    """

    model_config = ConfigDict(extra="ignore")

    status: Optional[OrderStatus] = None
    cargo_name: Optional[str] = Field(None, min_length=1, max_length=200)
    weight: Optional[Decimal] = Field(None, gt=0, description="Yuk og'irligi, tonna")
    price: Optional[Decimal] = Field(None, gt=0, description="Narx, UZS")
    currency: Optional[str] = Field(None, min_length=2, max_length=10)

    @field_validator("status", mode="before")
    @classmethod
    def upper_status(cls, v: Any) -> Any:
        return v.upper() if isinstance(v, str) else v


# ════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ════════════════════════════════════════════════════════════


class OrdersByDay(BaseModel):
    date: date
    count: int


class AdminDashboardStats(BaseModel):
    users_total: int
    users_today: int
    drivers_total: int
    drivers_online: int
    drivers_live_gps: int
    orders_total: int
    orders_today: int
    # Yakunlangan (COMPLETED) buyurtmalar bo'yicha umumiy aylanma — DB tomonda SUM bilan
    # hisoblanadi (sahifalangan ro'yxatni frontendda qo'shish noto'g'ri natija berardi).
    revenue_total: Decimal = Decimal("0")
    orders_by_status: Dict[str, int]
    orders_last_7_days: List[OrdersByDay]


# ════════════════════════════════════════════════════════════
# AI COMMANDS
# ════════════════════════════════════════════════════════════


class AICommandRead(BaseModel):
    id: int
    user_id: Optional[int]
    message_id: Optional[int]
    command_type: str
    raw_input: Optional[str]
    parameters: Optional[Dict[str, Any]] = None
    status: str
    result: Optional[Dict[str, Any]] = None
    error_msg: Optional[str] = None
    created_at: datetime
    executed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AICommandList(BaseModel):
    total: int
    items: List[AICommandRead]


# ════════════════════════════════════════════════════════════
# DRIVERS (blok / blokdan chiqarish)
# ════════════════════════════════════════════════════════════


class AdminDriverListItem(BaseModel):
    """Admin panel haydovchilar ro'yxati — balans va blok holati bilan."""

    driver_id: int
    user_id: int
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    truck_number: str
    truck_type_id: int
    balance: Decimal
    is_blocked: bool
    block_reason: Optional[str] = None
    # True bo'lsa — balans manfiy bo'lgani uchun tizim avtomatik bloklagan (admin qo'lda emas).
    blocked_for_debt: bool = False
    is_available: bool
    verification_status: str
    created_at: datetime


class AdminDriverList(BaseModel):
    total: int
    items: List[AdminDriverListItem]


class DriverBlockRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=300, description="Bloklash sababi (haydovchiga ko'rsatiladi)")


class DriverUnblockRequest(BaseModel):
    """Blokdan chiqarish. Balans hali manfiy bo'lsa ham admin ochib berishi mumkin —
    lekin keyingi komissiya yechilganda haydovchi yana avtomatik bloklanadi."""

    top_up_amount: Optional[Decimal] = Field(
        None,
        gt=0,
        description="Ixtiyoriy: blokdan chiqarish bilan birga balansga qo'shiladigan summa (qarzni yopish uchun)",
    )
    note: Optional[str] = Field(None, max_length=300, description="Balans tarixiga yoziladigan izoh")


# ════════════════════════════════════════════════════════════
# DRIVER LIVE LOCATION
# ════════════════════════════════════════════════════════════


class MonitorActiveOrder(BaseModel):
    """Haydovchi bajarayotgan buyurtma — xaritadagi kartochka uchun."""

    id: int
    cargo_name: str
    weight: Decimal
    volume: Optional[Decimal] = None
    price: Decimal
    currency: str
    status: str
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None
    current_waypoint_address: Optional[str] = None
    total_waypoints: int = 0
    completed_waypoints: int = 0


class DriverMonitorItem(BaseModel):
    """`GET /system/drivers/monitor` — xaritadagi bitta haydovchi (joylashuv + yuk holati)."""

    driver_id: int
    user_id: int
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    truck_type_name: Optional[str] = None
    truck_number: str
    is_available: bool
    is_blocked: bool
    block_reason: Optional[str] = None
    rating: Decimal
    total_trips: int

    # Xaritadagi marker rangi shu ikki maydonga qarab tanlanadi:
    #   busy=True  -> yuk bilan (ko'k), online & busy=False -> bo'sh (yashil), online=False -> kulrang
    online: bool = False
    busy: bool = False

    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # "live" — hozir translyatsiya qilyapti (Redis), "last_known" — DB'dagi oxirgi nuqta
    location_source: Optional[str] = None
    location_at: Optional[datetime] = None

    active_order: Optional[MonitorActiveOrder] = None


class DriverLocationItem(BaseModel):
    driver_id: int
    user_id: Optional[int] = None
    full_name: Optional[str] = None
    truck_number: Optional[str] = None
    truck_type_id: Optional[int] = None
    lat: float
    lon: float
    ts: datetime
    expires_at: Optional[datetime] = None


# ════════════════════════════════════════════════════════════
# KOMISSIYA / BALANS (billing)
# ════════════════════════════════════════════════════════════


class CommissionSettingsResponse(BaseModel):
    commission_percent: Decimal
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommissionSettingsUpdate(BaseModel):
    commission_percent: Decimal = Field(..., ge=0, le=100, description="Har bir order narxidan olinadigan foiz")


class BalanceAdjustRequest(BaseModel):
    amount: Decimal = Field(
        ..., description="Musbat = balansga qo'shish (to'ldirish), manfiy = balansdan yechish (tuzatish)"
    )
    note: Optional[str] = Field(None, max_length=300)

    @field_validator("amount")
    @classmethod
    def amount_not_zero(cls, v: Decimal) -> Decimal:
        if v == 0:
            raise ValueError("amount 0 bo'lishi mumkin emas")
        return v


class BalanceTransactionResponse(BaseModel):
    id: int
    user_id: int
    type: str
    amount: Decimal
    balance_after: Decimal
    order_id: Optional[int] = None
    created_by_admin_id: Optional[int] = None
    note: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("type", mode="before")
    @classmethod
    def enum_to_value(cls, v):
        return v.value if hasattr(v, "value") else v
