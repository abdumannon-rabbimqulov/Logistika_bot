from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import ADMIN_IDS, get_db
from driver.crud import get_driver_by_user_id
from order import crud, schemas
from order.models import Order
from services import yandex_geocoder
from users.auth import get_current_active_user, get_current_sender
from users.models import User, UserRole

router = APIRouter(prefix="/orders", tags=["Buyurtmalar (Orders)"])


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
             summary="Buyurtmaga haydovchini biriktirish")
async def assign_driver_to_order(
    order_id: int,
    data: schemas.OrderAssignDriver,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")

    if current_user.role == UserRole.DRIVER:
        driver = await get_driver_by_user_id(db, current_user.id)
        if not driver or driver.id != data.driver_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat o'zingizni biriktira olasiz")
        if driver.is_blocked:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Siz bloklangansiz — buyurtma qabul qila olmaysiz. Sababi: " + (driver.block_reason or "noma'lum"),
            )
    elif not _is_admin(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    if order.driver_id is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Buyurtmaga allaqachon haydovchi biriktirilgan")

    return await crud.assign_driver(db, order, data.driver_id)


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
