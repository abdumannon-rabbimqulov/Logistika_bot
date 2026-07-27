from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from order.dispatch_models import DispatchAttemptStatus, DispatchMatchType
from order.models import OrderStatus, WaypointStatus, WaypointType



class OrderWaypointBase(BaseModel):
    sequence: int = Field(..., ge=1, description="Nuqta tartibi: 1 - pickup, oxirgisi - delivery")
    type: WaypointType
    address: Optional[str] = Field(None, max_length=300)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    contact_name: Optional[str] = Field(None, max_length=150)
    contact_phone: Optional[str] = Field(None, max_length=20)


class OrderWaypointCreate(OrderWaypointBase):
    """Buyurtma yaratishda kelayotgan waypoint (status kiritilmaydi, default PENDING).

    Ikkala holat ham qabul qilinadi:
    - faqat `address` (matn) — backend Yandex Geocoder orqali koordinatani topadi;
    - faqat `latitude`/`longitude` (masalan Telegram "joylashuvni yuborish") — backend
      manzil matnini reverse-geocoding orqali topadi.
    Ikkalasi ham berilishi mumkin — bu holda berilgan qiymatlar ustuvor, qidiruv qilinmaydi.
    """

    @model_validator(mode="after")
    def check_address_or_coordinates(self) -> "OrderWaypointCreate":
        has_coords = self.latitude is not None and self.longitude is not None
        has_address = bool(self.address and self.address.strip())
        if not has_coords and not has_address:
            raise ValueError(
                "Har bir nuqta uchun manzil matni yoki koordinata (latitude+longitude) kiritilishi shart"
            )
        return self


class WaypointProgressUpdate(BaseModel):
    """Haydovchi nuqtadagi qadamni belgilaydi ("Yetib keldim" / "Yukni ortdim").

    `latitude`/`longitude` — tugma bosilgan paytda olingan YANGI o'lchov. Bu geofence
    uchun asosiy manba: Telegram WebApp fonga o'tganda OS jonli kuzatuvni to'xtatadi,
    shuning uchun serverdagi "oxirgi ma'lum nuqta"ga tayanib bo'lmaydi. Berilmasa —
    Redis'dagi yangi koordinata zaxira sifatida ishlatiladi (services/geofence.py).

    `override_reason` — faqat admin uchun: GPS nosoz bo'lgan holatda qadamni qo'lda
    tasdiqlaydi va sabab nuqtaga yozib qo'yiladi.
    """

    status: WaypointStatus
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    accuracy: Optional[float] = Field(None, ge=0, description="GPS aniqligi, metrda")
    override_reason: Optional[str] = Field(None, max_length=300)


class OrderWaypointResponse(OrderWaypointBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    status: WaypointStatus
    created_at: datetime

    # Qadam vaqtlari va GPS isboti — haydovchi ilovasida va admin panelida ko'rsatiladi.
    arrived_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    confirmed_distance_m: Optional[int] = None
    confirmed_accuracy_m: Optional[int] = None
    override_by_user_id: Optional[int] = None
    override_reason: Optional[str] = None


# ============================================================
#  Order sxemalari
# ============================================================

class OrderBase(BaseModel):
    cargo_name: str = Field(..., max_length=200)
    weight: Decimal = Field(..., gt=0, description="Yuk og'irligi, tonna")
    volume: Optional[Decimal] = Field(None, gt=0, description="Yuk hajmi, m³")
    pickup_at: datetime
    required_truck_type_id: int


class OrderCreate(OrderBase):
    """Yangi buyurtma yaratish uchun (mijoz tomonidan yuboriladi).

    `price`/`currency` bu yerda YO'Q — narx mijozdan ishonch bilan qabul qilinmaydi,
    backend marshrutni (OSRM) hisoblab, tanlangan `required_truck_type_id` narxlariga
    (`TruckType.calculate_price`) qarab serverda avtomatik hisoblaydi.
    """

    waypoints: list[OrderWaypointCreate] = Field(..., min_length=2)

    @field_validator("pickup_at")
    @classmethod
    def validate_pickup_at_not_in_past(cls, value: datetime) -> datetime:
        # Soat mintaqasiz (naive) qiymat kelsa UTC deb qabul qilinadi (DB ustuni timezone=True).
        aware_value = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        # 1 daqiqalik imtiyoz — mijoz "hozir" tanlaganda so'rov tarmoqda kechikishi mumkin.
        if aware_value < datetime.now(timezone.utc) - timedelta(minutes=1):
            raise ValueError("Yuklash vaqti (pickup_at) o'tmishda bo'lishi mumkin emas")
        return value

    @field_validator("waypoints")
    @classmethod
    def validate_waypoints(cls, waypoints: list[OrderWaypointCreate]) -> list[OrderWaypointCreate]:
        # Kamida bitta PICKUP va bitta DELIVERY nuqtasi bo'lishi shart
        types = [wp.type for wp in waypoints]
        if WaypointType.PICKUP not in types:
            raise ValueError("Kamida bitta PICKUP nuqtasi bo'lishi kerak")
        if WaypointType.DELIVERY not in types:
            raise ValueError("Kamida bitta DELIVERY nuqtasi bo'lishi kerak")

        # sequence'lar 1 dan boshlab ketma-ket bo'lishi kerak
        sequences = sorted(wp.sequence for wp in waypoints)
        if sequences != list(range(1, len(waypoints) + 1)):
            raise ValueError("waypoints.sequence 1 dan boshlab ketma-ket bo'lishi kerak")

        return waypoints


class OrderUpdate(BaseModel):
    """Buyurtmani qisman yangilash — `PATCH /orders/{id}`, buyurtma egasi uchun.

    DIQQAT: bu sxemada tizim boshqaradigan maydonlar ATAYLAB YO'Q.

    Ilgari bu yerda `status`, `driver_id`, `price`, `currency`, `total_distance_km` va
    `departure_at` ham bor edi, `crud.update_order` esa ularni to'g'ridan-to'g'ri
    `UPDATE` qilardi. Natijada buyurtma egasi o'z buyurtmasiga `status=COMPLETED`
    yozib, `/status` endpointidagi 403 himoyasini butunlay chetlab o'ta olardi —
    bunda `completed_at` ham yozilmasdi, komissiya ham yechilmasdi. Xuddi shunday
    yo'l bilan `price` ni tushirib komissiya bazasini kamaytirish yoki `driver_id` ni
    o'zgartirib boshqa haydovchini biriktirish mumkin edi.

    Endi: statusni admin `PATCH /orders/{id}/status` orqali, haydovchi esa marshrut
    nuqtalari orqali o'zgartiradi; narxni oshirish `POST /orders/{id}/price-bump`
    orqali; masofa/narx esa OSRM bo'yicha faqat server tomonida hisoblanadi.
    """

    model_config = ConfigDict(extra="forbid")

    cargo_name: Optional[str] = Field(None, max_length=200)
    weight: Optional[Decimal] = Field(None, gt=0)
    volume: Optional[Decimal] = Field(None, gt=0)
    pickup_at: Optional[datetime] = None
    required_truck_type_id: Optional[int] = None


class OrderStatusUpdate(BaseModel):
    """Faqat statusni o'zgartirish uchun qisqartirilgan sxema"""
    status: OrderStatus


class OrderAssignDriver(BaseModel):
    """Haydovchini buyurtmaga biriktirish"""
    driver_id: int = Field(..., gt=0)


class AssignedDriverInfo(BaseModel):
    """Biriktirilgan haydovchi haqida qisqa ma'lumot (admin panel javobda ko'rsatadi)."""

    driver_id: int
    user_id: int
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    truck_number: str
    truck_type_id: int
    is_available: bool
    is_blocked: bool
    verification_status: str
    rating: Decimal
    total_trips: int


class OrderResponse(OrderBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    driver_id: Optional[int] = None
    departure_at: Optional[datetime] = None
    total_distance_km: Optional[Decimal] = None
    price: Decimal
    original_price: Optional[Decimal] = None
    currency: str
    status: OrderStatus
    dispatch_round: int = 0
    price_bump_requested_at: Optional[datetime] = None
    overload_warning: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    waypoints: list[OrderWaypointResponse] = []


class OrderListItem(BaseModel):
    """Ro'yxat (list) ko'rinishi uchun yengillashtirilgan sxema"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    cargo_name: str
    weight: Decimal
    price: Decimal
    currency: str
    status: OrderStatus
    pickup_at: datetime
    driver_id: Optional[int] = None
    overload_warning: Optional[str] = None
    created_at: datetime
    # Yakunlangan buyurtmalar uchun to'ldiriladi — haydovchi daromadi shu sana bo'yicha
    # guruhlanadi (created_at emas: yuk boshqa haftada yaratilgan bo'lishi mumkin).
    completed_at: Optional[datetime] = None


class OrderDetailResponse(OrderResponse):
    """To'liq batafsil ko'rinish: origin/destination alohida ajratib chiqarilgan"""

    origin: Optional[OrderWaypointResponse] = None
    destination: Optional[OrderWaypointResponse] = None
    current_waypoint: Optional[OrderWaypointResponse] = None

    @classmethod
    def from_order(cls, order) -> "OrderDetailResponse":
        """Order ORM obyektidagi property'larni (origin/destination/current_waypoint) sxemaga joylash"""
        base = cls.model_validate(order)
        base.origin = OrderWaypointResponse.model_validate(order.origin) if order.origin else None
        base.destination = OrderWaypointResponse.model_validate(order.destination) if order.destination else None
        base.current_waypoint = (
            OrderWaypointResponse.model_validate(order.current_waypoint) if order.current_waypoint else None
        )
        return base


class OrderAssignDriverResponse(BaseModel):
    """`POST /orders/{id}/assign-driver` javobi: yangilangan buyurtma + haydovchi holati."""

    order: OrderDetailResponse
    driver: AssignedDriverInfo


# ============================================================
#  Manzil qidirish (Yandex Geocoder)
# ============================================================

class GeocodeSuggestion(BaseModel):
    """Manzil matni bo'yicha qidiruv natijasi (autocomplete uchun)."""
    address: str
    latitude: float
    longitude: float


class ReverseGeocodeResponse(BaseModel):
    """Koordinata bo'yicha topilgan manzil (sender o'z joylashuvini yuborganda)."""
    address: Optional[str] = None
    latitude: float
    longitude: float


# ============================================================
#  Narx taklifi (Price estimate)
# ============================================================

class PriceEstimateLocation(BaseModel):
    """Manzil matni yoki koordinata — ikkalasidan kamida bittasi berilishi shart."""
    address: Optional[str] = Field(None, max_length=300)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)

    @model_validator(mode="after")
    def check_address_or_coordinates(self) -> "PriceEstimateLocation":
        has_coords = self.latitude is not None and self.longitude is not None
        has_address = bool(self.address and self.address.strip())
        if not has_coords and not has_address:
            raise ValueError(
                "Manzil matni yoki koordinata (latitude+longitude) kiritilishi shart"
            )
        return self


class PriceEstimateRequest(BaseModel):
    """Pickup va delivery nuqtalari bo'yicha barcha mashina turlari uchun narx so'rovi."""
    origin: PriceEstimateLocation
    destination: PriceEstimateLocation


class TruckTypePriceOption(BaseModel):
    truck_type_id: int
    name: str
    image_url: Optional[str] = None
    price: Decimal
    currency: str = "UZS"


class PriceEstimateResponse(BaseModel):
    origin_address: Optional[str] = None
    origin_latitude: float
    origin_longitude: float
    destination_address: Optional[str] = None
    destination_latitude: float
    destination_longitude: float
    distance_km: Decimal
    duration_min: Decimal
    # OSRM marshrut chizig'i: [[latitude, longitude], ...] — mijozga xaritada ko'rsatish uchun
    route_geometry: list[tuple[float, float]] = []
    options: list[TruckTypePriceOption]


# ============================================================
#  Avtomatik dispatch (docs/DISPATCH_SYSTEM_PLAN.md)
# ============================================================

class DispatchOrderSummary(BaseModel):
    """Taklif kartasida ko'rsatish uchun buyurtma xulosasi (WebApp).

    Pending dispatch paytida haydovchi hali biriktirilmagani uchun `GET /orders/{id}`
    orqali buyurtmani o'qiy olmaydi (403) — shu sabab taklif javobiga shu yengil
    xulosa qo'shiladi (yo'nalish/og'irlik/narx). Batafsil ma'lumot qabul qilingach
    `POST /dispatch/{id}/accept` javobidagi to'liq OrderDetailResponse'dan olinadi.
    """
    model_config = ConfigDict(from_attributes=True)

    cargo_name: str
    weight: Decimal
    price: Decimal
    currency: str
    origin_address: Optional[str] = None
    destination_address: Optional[str] = None

    # A→B marshrut ma'lumotlari — taklif kartasidagi "N km" va xaritadagi chiziq uchun.
    # DIQQAT: bu `DispatchAttemptResponse.distance_km` DAN BOSHQA narsa — u haydovchidan
    # yuk ortish nuqtasigacha bo'lgan masofa (haydovchi A nuqtada tursa ~0 km bo'ladi),
    # bu esa buyurtmaning o'z uzunligi (Toshkent→Samarqand ≈ 280 km).
    total_distance_km: Optional[Decimal] = None
    origin_latitude: Optional[float] = None
    origin_longitude: Optional[float] = None
    destination_latitude: Optional[float] = None
    destination_longitude: Optional[float] = None
    # OSRM marshrut chizig'i: [[latitude, longitude], ...] — buyurtma yaratilganda
    # PostGIS'ga saqlangan geometriyadan o'qiladi (qayta OSRM so'rovi yuborilmaydi).
    route_geometry: list[tuple[float, float]] = []


class DispatchAttemptResponse(BaseModel):
    """Haydovchiga yuborilgan joriy taklif (WebApp `GET /orders/dispatch/active` uchun)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    driver_id: int
    round_number: int
    match_type: DispatchMatchType
    distance_km: Optional[Decimal] = None
    status: DispatchAttemptStatus
    sent_at: datetime
    expires_at: datetime
    # Taklif kartasi uchun buyurtma xulosasi — /dispatch/active endpointida to'ldiriladi.
    order: Optional[DispatchOrderSummary] = None


class PriceBumpRequest(BaseModel):
    """Sender barcha urinishlar rad etilgandan keyin narxni oshiradi."""
    price: Decimal = Field(..., gt=0)