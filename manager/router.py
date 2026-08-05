"""Menejer paneli — buyurtmalarni operativ boshqarish.

Menejerning huquqlari ATAYLAB tor:

    ✅ buyurtmalar ro'yxatini va tafsilotini ko'rish (narxsiz)
    ✅ buyurtma holatini yangilash
    ✅ buyurtmaga yuk mashinasini tanlab biriktirish
    ❌ moliya — balans, komissiya, narx sozlamalari, buyurtma narxi

Moliya bloki ikki qavatda ishlaydi:

1. Endpoint darajasi — moliyaviy amallarning HAMMASI `/system` ostida va
   `Admin_panel.validation.is_admin` bilan himoyalangan. Bu dependency menejerni
   o'tkazmaydi, shuning uchun `/manager` ga kirish huquqi hech qachon `/system` ga
   aylanib ketmaydi. Bu yerda "moliyani yashiradigan" kod yozilmaydi — teskarisi,
   moliya endpointlari BU router'da umuman yo'q.
2. Maydon darajasi — javob sxemalari (`manager/schemas.py`) narx maydonlarini
   umuman e'lon qilmaydi, umumiy `/orders/...` javoblari esa menejer uchun
   `strip_finance_fields()` bilan tozalanadi (`order/router.py`).

Router butunlay `Depends(get_current_staff)` bilan yopilgan (endpoint-ma-endpoint
emas): `Admin_panel/router.py` da har bir funksiyaga qo'lda `Depends(is_admin)`
yozilgan va bitta funksiyada uni unutish huquq teshigiga aylanadi. Bu yerda
himoyani unutib bo'lmaydi.

Nega admin ham kiritilgan (`get_current_staff` = admin | manager): admin menejer
ko'rayotgan ekranni ko'ra olishi kerak, aks holda nosozlikni tekshirish uchun
ikkinchi hisob ochishga to'g'ri kelardi.
"""

from __future__ import annotations

import logging
from typing import List, NoReturn, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import get_db
from driver.crud import get_driver
from driver.models import Driver, TruckType
from manager import schemas
from order import crud as order_crud
from order.models import Order, OrderStatus
from services import dispatch as dispatch_service
from services import queue
from users.models import User
from users.permissions import get_current_staff

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/manager",
    tags=["Manager paneli"],
    dependencies=[Depends(get_current_staff)],
)


def _raise_dispatch_error(exc: dispatch_service.DispatchError) -> NoReturn:
    raise HTTPException(exc.status_code, detail=str(exc)) from exc


async def _get_order_or_404(db: AsyncSession, order_id: int) -> Order:
    order = await order_crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")
    return order


def _truck_from_driver(driver: Driver, truck_type: TruckType) -> schemas.AvailableTruck:
    return schemas.AvailableTruck(
        driver_id=driver.id,
        truck_number=driver.truck_number,
        truck_type_id=driver.truck_type_id,
        truck_type_name=truck_type.name,
        truck_year=driver.truck_year,
        max_weight=truck_type.max_weight,
        max_volume=truck_type.max_volume,
        rating=driver.rating,
        total_trips=driver.total_trips,
        is_available=driver.is_available,
        is_blocked=driver.is_blocked,
        verification_status=driver.verification_status.value,
        current_city=driver.current_city,
        current_region=driver.current_region,
    )


@router.get(
    "/orders",
    response_model=List[schemas.ManagerOrderListItem],
    summary="Buyurtmalar ro'yxati (narxsiz)",
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    order_status: Optional[OrderStatus] = Query(
        None, alias="status", description="Holat bo'yicha filtr"
    ),
    unassigned: bool = Query(False, description="Faqat haydovchi biriktirilmaganlar"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    stmt = select(Order).order_by(Order.created_at.desc()).limit(limit).offset(offset)
    if order_status is not None:
        stmt = stmt.where(Order.status == order_status)
    if unassigned:
        stmt = stmt.where(Order.driver_id.is_(None))

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/orders/{order_id}",
    response_model=schemas.ManagerOrderDetail,
    summary="Buyurtma tafsiloti (narxsiz)",
)
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    order = await _get_order_or_404(db, order_id)
    return schemas.ManagerOrderDetail.from_order(order)


@router.patch(
    "/orders/{order_id}/status",
    response_model=schemas.ManagerOrderDetail,
    summary="Buyurtma holatini yangilash",
)
async def update_order_status(
    order_id: int,
    data: schemas.ManagerOrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff),
):
    """Holatlar o'rtasidagi ruxsat etilgan o'tishlar `services/order_flow.py` da.

    Menejer ham o'sha qoidalarga bo'ysunadi: masalan COMPLETED buyurtmani qayta ochib
    komissiyani ikki marta yechish yo'li yo'q. Qoida buzilsa `OrderFlowError` chiqadi
    va global handler uni 400 qilib qaytaradi (`middlewares/error_handler.py`).
    """
    order = await _get_order_or_404(db, order_id)
    order = await order_crud.update_order_status(
        db,
        order,
        data.status,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value if current_user.role else None,
    )
    return schemas.ManagerOrderDetail.from_order(order)


@router.get(
    "/orders/{order_id}/available-trucks",
    response_model=List[schemas.AvailableTruck],
    summary="Buyurtmaga mos yuk mashinalari ro'yxati",
)
async def list_available_trucks(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    only_free: bool = Query(
        True, description="Faqat bo'sh (is_available) va bloklanmagan mashinalar"
    ),
    any_truck_type: bool = Query(
        False, description="Buyurtma talab qilgan mashina turidan boshqasini ham ko'rsatish"
    ),
):
    """Alohida `trucks` jadvali yo'q — mashina haydovchi profilida saqlanadi
    (`drivers.truck_number` + `drivers.truck_type_id`), shuning uchun ro'yxat
    haydovchilar jadvalidan yig'iladi.

    Standart holatda buyurtmaning `required_truck_type_id` iga mos, tasdiqlangan va
    bo'sh mashinalar qaytadi. `any_truck_type=true` — favqulodda holatlar uchun
    (mos mashina topilmaganda menejer boshqasini tanlashi mumkin).
    """
    order = await _get_order_or_404(db, order_id)

    stmt = (
        select(Driver, TruckType)
        .join(TruckType, Driver.truck_type_id == TruckType.id)
        .order_by(Driver.rating.desc(), Driver.total_trips.desc())
    )
    if not any_truck_type:
        stmt = stmt.where(Driver.truck_type_id == order.required_truck_type_id)
    if only_free:
        stmt = stmt.where(
            Driver.is_blocked.is_(False),
            Driver.is_available.is_(True),
            Driver.docs_verified.is_(True),
        )

    result = await db.execute(stmt)
    return [_truck_from_driver(driver, truck_type) for driver, truck_type in result.all()]


@router.post(
    "/orders/{order_id}/assign-truck",
    response_model=schemas.AssignTruckResponse,
    summary="Buyurtmaga yuk mashinasini biriktirish",
)
async def assign_truck(
    order_id: int,
    data: schemas.AssignTruckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_staff),
):
    """Biriktirish mantiqi `services/dispatch.py: assign_driver_manually()` da —
    u atomik `WHERE driver_id IS NULL` yangilashni, ochiq qolgan takliflarni bekor
    qilishni va haydovchi/sender'ga xabar yuborishni birga bajaradi. Shu sababli bu
    yerda takrorlanmaydi: aks holda ikki xil biriktirish yo'li paydo bo'lib, biri
    bildirishnomasiz qolardi.
    """
    order = await _get_order_or_404(db, order_id)

    driver = await get_driver(db, data.driver_id)
    if not driver:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Mashina (haydovchi id={data.driver_id}) topilmadi",
        )

    try:
        order = await dispatch_service.assign_driver_manually(db, order, driver)
    except dispatch_service.DispatchError as exc:
        _raise_dispatch_error(exc)

    truck_type = await db.get(TruckType, driver.truck_type_id)

    await queue.publish_event(
        queue.EVENT_ORDER_TRUCK_ASSIGNED,
        {
            "order_id": order.id,
            "customer_id": order.customer_id,
            "driver_id": driver.id,
            "truck_number": driver.truck_number,
            "truck_type_id": driver.truck_type_id,
            "assigned_by_user_id": current_user.id,
            "assigned_by_role": current_user.role.value if current_user.role else None,
        },
    )

    return schemas.AssignTruckResponse(
        order=schemas.ManagerOrderDetail.from_order(order),
        truck=_truck_from_driver(driver, truck_type),
    )
