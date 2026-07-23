from __future__ import annotations

from typing import List, NoReturn, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import ADMIN_IDS, get_db
from driver.crud import get_driver_by_user_id
from order import crud, schemas
from order.models import Order
from services import dispatch as dispatch_service
from services import osrm_client, yandex_geocoder
from users.auth import get_current_active_user, get_current_sender
from users.models import User, UserRole

router = APIRouter(prefix="/orders", tags=["Buyurtmalar (Orders)"])


def _routing_unavailable() -> HTTPException:
    """OSRM ishlamayotganda qaytariladigan javob.

    503 (422 emas), chunki bu mijozning xatosi emas — u manzilni o'zgartirib qayta
    urinsa ham natija bo'lmaydi. Xatoning ichki matni (OSRM manzili, httpx tafsilotlari)
    mijozga berilmaydi — u faqat logga yoziladi (services/osrm_client.py).
    """
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Marshrut xizmati vaqtincha ishlamayapti, biroz kutib qayta urinib ko'ring",
    )


def _raise_dispatch_error(exc: dispatch_service.DispatchError) -> NoReturn:
    raise HTTPException(exc.status_code, detail=str(exc)) from exc


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN or user.id in ADMIN_IDS


async def _require_order_access(db: AsyncSession, order_id: int, current_user: User) -> Order:
    """Buyurtmani topadi va faqat egasi/biriktirilgan haydovchi/admin ko'ra olishini tekshiradi."""
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")

    if _is_admin(current_user) or order.customer_id == current_user.id:
        return order

    driver = await get_driver_by_user_id(db, current_user.id)
    if driver and order.driver_id == driver.id:
        return order

    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Bu buyurtmaga kirish huquqingiz yo'q")


@router.post("", response_model=schemas.OrderDetailResponse, status_code=status.HTTP_201_CREATED,
             summary="Yangi buyurtma yaratish (sender)")
async def create_order(
    data: schemas.OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_sender),
):
    try:
        order = await crud.create_order(db, data, customer_id=current_user.id)
    except osrm_client.OSRMUnavailableError as exc:
        raise _routing_unavailable() from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return schemas.OrderDetailResponse.from_order(order)


@router.get("", response_model=List[schemas.OrderListItem], summary="Mening buyurtmalarim")
async def list_my_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.DRIVER:
        driver = await get_driver_by_user_id(db, current_user.id)
        if not driver:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Haydovchi profili topilmadi")
        return await crud.list_orders_by_driver(db, driver.id)
    return await crud.list_orders_by_customer(db, current_user.id)


@router.get("/available/list", response_model=List[schemas.OrderListItem],
            summary="Haydovchisi topilmagan buyurtmalar (haydovchi uchun)")
async def list_available_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    truck_type_id: Optional[int] = Query(None),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Bu ro'yxat faqat haydovchilar uchun")
    return await crud.list_available_orders(db, truck_type_id=truck_type_id)


@router.get("/geocode/search", response_model=List[schemas.GeocodeSuggestion],
            summary="Manzil qidirish (Yandex Geocoder, autocomplete)")
async def search_address(
    q: str = Query(..., min_length=3, description="Qidirilayotgan manzil matni"),
    _: User = Depends(get_current_active_user),
):
    results = await yandex_geocoder.search_address(q)
    return [
        schemas.GeocodeSuggestion(address=r.address, latitude=r.latitude, longitude=r.longitude)
        for r in results
    ]


@router.get("/geocode/reverse", response_model=schemas.ReverseGeocodeResponse,
            summary="Koordinata bo'yicha manzilni aniqlash (sender o'z joylashuvini yuborganda)")
async def reverse_geocode(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    _: User = Depends(get_current_active_user),
):
    address = await yandex_geocoder.reverse_geocode(latitude, longitude)
    return schemas.ReverseGeocodeResponse(address=address, latitude=latitude, longitude=longitude)


@router.post("/estimate-price", response_model=schemas.PriceEstimateResponse,
             summary="Manzillar bo'yicha barcha mashina turlari uchun narx taklifi")
async def estimate_price(
    data: schemas.PriceEstimateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    try:
        return await crud.estimate_price(db, data)
    except osrm_client.OSRMUnavailableError as exc:
        raise _routing_unavailable() from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{order_id}", response_model=schemas.OrderDetailResponse, summary="Buyurtma tafsilotlari")
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await _require_order_access(db, order_id, current_user)
    return schemas.OrderDetailResponse.from_order(order)


@router.patch("/{order_id}", response_model=schemas.OrderDetailResponse, summary="Buyurtmani tahrirlash (egasi)")
async def update_order(
    order_id: int,
    data: schemas.OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await _require_order_access(db, order_id, current_user)
    if not _is_admin(current_user) and order.customer_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat buyurtma egasi tahrirlay oladi")
    order = await crud.update_order(db, order, data)
    return schemas.OrderDetailResponse.from_order(order)


@router.patch("/{order_id}/status", response_model=schemas.OrderResponse,
              summary="Buyurtma holatini yangilash (faqat biriktirilgan haydovchi yoki admin)")
async def update_order_status(
    order_id: int,
    data: schemas.OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await _require_order_access(db, order_id, current_user)

    is_assigned_driver = False
    if current_user.role == UserRole.DRIVER:
        driver = await get_driver_by_user_id(db, current_user.id)
        is_assigned_driver = bool(driver and order.driver_id == driver.id)

    if not _is_admin(current_user) and not is_assigned_driver:
        # Sender (mijoz) buyurtmani ko'ra oladi, lekin holatini o'zgartira olmaydi —
        # bu haydovchi/admin ixtiyorida (masalan sender "COMPLETED" qo'yib komissiyani
        # o'zboshimchalik bilan ishga tushirmasligi uchun).
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Buyurtma holatini faqat biriktirilgan haydovchi yoki admin o'zgartira oladi",
        )

    return await crud.update_order_status(db, order, data.status)


@router.post("/{order_id}/assign-driver", response_model=schemas.OrderResponse,
             summary="Buyurtmaga qo'lda haydovchi biriktirish (faqat admin — favqulodda holat)")
async def assign_driver_to_order(
    order_id: int,
    data: schemas.OrderAssignDriver,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Oddiy oqimda haydovchi buyurtmani `POST /orders/dispatch/{attempt_id}/accept` orqali,
    # navbat bilan kelgan taklifni qabul qilib oladi (services/dispatch.py). Bu endpoint
    # endi faqat admin uchun — masalan avtomatik dispatch ishlamay qolgan holatlarda qo'lda
    # tuzatish uchun. Avval driverlar bu yerdan o'zini to'g'ridan-to'g'ri biriktira olardi —
    # bu ochiq ro'yxatda lock yo'q edi va poyga sharoitiga (race condition) olib kelardi.
    if not _is_admin(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")

    updated = await crud.assign_driver(db, order, data.driver_id)
    if updated is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Buyurtmaga allaqachon haydovchi biriktirilgan")
    return updated


@router.get("/dispatch/active", response_model=Optional[schemas.DispatchAttemptResponse],
            summary="Haydovchining joriy faol dispatch taklifi (WebApp sinxronlash uchun)")
async def get_active_dispatch(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat haydovchilar uchun")
    driver = await get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Haydovchi profili topilmadi")
    attempt = await dispatch_service.get_active_attempt(db, driver.id)
    return schemas.DispatchAttemptResponse.model_validate(attempt) if attempt else None


@router.post("/dispatch/{attempt_id}/accept", response_model=schemas.OrderDetailResponse,
             summary="Haydovchi navbat bilan kelgan taklifni qabul qiladi")
async def accept_dispatch(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat haydovchilar uchun")
    try:
        order = await dispatch_service.accept_attempt(db, attempt_id, acting_user_id=current_user.id)
    except dispatch_service.DispatchError as exc:
        _raise_dispatch_error(exc)
    return schemas.OrderDetailResponse.from_order(order)


@router.post("/dispatch/{attempt_id}/reject", status_code=status.HTTP_204_NO_CONTENT,
             summary="Haydovchi taklifni rad etadi — navbat keyingi nomzodga o'tadi")
async def reject_dispatch(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat haydovchilar uchun")
    try:
        await dispatch_service.reject_attempt(db, attempt_id, acting_user_id=current_user.id)
    except dispatch_service.DispatchError as exc:
        _raise_dispatch_error(exc)


@router.post("/{order_id}/price-bump", response_model=schemas.OrderDetailResponse,
             summary="Sender narxni oshirib qidiruvni davom ettiradi (5 urinish rad etilgandan keyin)")
async def price_bump_order(
    order_id: int,
    data: schemas.PriceBumpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_sender),
):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")
    if order.customer_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat buyurtma egasi narxni oshira oladi")
    try:
        order = await dispatch_service.apply_price_bump(db, order, data.price)
    except dispatch_service.DispatchError as exc:
        _raise_dispatch_error(exc)
    return schemas.OrderDetailResponse.from_order(order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Buyurtmani bekor qilish (egasi)")
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await _require_order_access(db, order_id, current_user)
    if not _is_admin(current_user) and order.customer_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat buyurtma egasi o'chira oladi")
    await crud.delete_order(db, order)
