

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from Admin_panel import crud as admin_crud
from Admin_panel import schemas as admin_schemas
from Admin_panel.validation import is_admin
from config.config import ADMIN_IDS, async_session, get_db
from order import crud as order_crud
from order import schemas as order_schemas
from services import billing, live_location
from users import crud as user_crud
from users.auth import verify_token
from users.models import User, UserRole

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["Admin paneli"])





@router.get("/dashboard/stats", response_model=admin_schemas.AdminDashboardStats)
async def admin_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
):
    return await admin_crud.dashboard_stats(db)


# ════════════════════════════════════════════════════════════
# USERS
# ════════════════════════════════════════════════════════════


@router.get("/users", response_model=admin_schemas.AdminUserList)
async def admin_list_users(
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
    role: Optional[UserRole] = None,
    is_banned: Optional[bool] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    rows, total = await admin_crud.list_users(
        db,
        role=role,
        is_banned=is_banned,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return admin_schemas.AdminUserList(total=total, items=rows)


@router.get("/users/{user_id}", response_model=admin_schemas.AdminUserListItem)
async def admin_get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
):
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")
    return user


@router.patch("/users/{user_id}", response_model=admin_schemas.AdminUserListItem)
async def admin_update_user(
    user_id: int,
    data: admin_schemas.AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
):
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")
    return await admin_crud.update_user_admin(db, user, data)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_deactivate_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
):
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")
    await user_crud.deactivate_user(db, user)


# ════════════════════════════════════════════════════════════
# ORDERS (admin moderation)
# ════════════════════════════════════════════════════════════


@router.get("/orders", response_model=List[order_schemas.OrderResponse])
async def admin_list_orders(
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
    status_filter: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    rows, total = await admin_crud.list_orders_admin(
        db,
        status=status_filter,
        customer_id=customer_id,
        driver_id=driver_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return rows


@router.patch(
    "/orders/{order_id}",
    response_model=order_schemas.OrderResponse,
    summary="Buyurtmani tahrirlash / statusini o'zgartirish (admin)",
)
async def admin_update_order(
    order_id: int,
    data: admin_schemas.AdminOrderUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(is_admin),
):
    """Qisman yangilash: so'rovda kelgan maydonlar qo'llaniladi.

    Avval oddiy maydonlar (narx, yuk nomi...), keyin status — shu tartibda, chunki
    COMPLETED ga o'tishda komissiya YANGI narxdan hisoblanishi kerak.
    """
    order = await order_crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi.")

    await admin_crud.update_order_admin(db, order, data)

    if data.status is not None and data.status != order.status:
        # Komissiya, completed_at va admin ogohlantirishlari shu funksiya ichida.
        await order_crud.update_order_status(db, order, data.status)

    logger.info("Admin #%s buyurtma #%s ni yangiladi: %s", admin.id, order_id, data.model_dump(exclude_unset=True))

    # `waypoints`/`route` bilan qayta yuklab qaytaramiz: yuqoridagi commit/refresh'lar
    # bu bog'lanishlarni expire qilgan bo'lishi mumkin (sinxron serializatsiya = MissingGreenlet).
    return await order_crud.get_order(db, order_id)


# ════════════════════════════════════════════════════════════
# DRIVERS (blok / blokdan chiqarish)
# ════════════════════════════════════════════════════════════


def _driver_item(driver, user) -> admin_schemas.AdminDriverListItem:
    return admin_schemas.AdminDriverListItem(
        driver_id=driver.id,
        user_id=user.id,
        full_name=user.full_name,
        phone_number=user.phone_number,
        truck_number=driver.truck_number,
        truck_type_id=driver.truck_type_id,
        balance=user.balance or 0,
        is_blocked=driver.is_blocked,
        block_reason=driver.block_reason,
        blocked_for_debt=driver.is_blocked and driver.block_reason == billing.DEBT_BLOCK_REASON,
        is_available=driver.is_available,
        verification_status=driver.verification_status.value,
        created_at=driver.created_at,
    )


async def _get_driver_or_404(db: AsyncSession, driver_id: int):
    pair = await admin_crud.get_driver_with_user(db, driver_id)
    if not pair:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Haydovchi topilmadi.")
    return pair


@router.get(
    "/drivers",
    response_model=admin_schemas.AdminDriverList,
    summary="Haydovchilar ro'yxati (balans va blok holati bilan)",
)
async def admin_list_drivers(
    response: Response,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
    is_blocked: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    rows, total = await admin_crud.list_drivers_admin(
        db, is_blocked=is_blocked, search=search, skip=skip, limit=limit
    )
    response.headers["X-Total-Count"] = str(total)
    return admin_schemas.AdminDriverList(
        total=total, items=[_driver_item(driver, user) for driver, user in rows]
    )


@router.post(
    "/drivers/{driver_id}/unblock",
    response_model=admin_schemas.AdminDriverListItem,
    summary="Haydovchini blokdan chiqarish (qarzga tushib bloklanganlar uchun ham)",
)
async def admin_unblock_driver(
    driver_id: int,
    data: Optional[admin_schemas.DriverUnblockRequest] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(is_admin),
):
    """Balans manfiy bo'lsa ham ochib berish mumkin — bu adminning qarori.

    Diqqat: balans manfiyligicha qolsa, keyingi yakunlangan buyurtma komissiyasi
    yechilganda haydovchi yana avtomatik bloklanadi (services/billing.py). Qarzni
    darhol yopish uchun `top_up_amount` yuboriladi.
    """
    driver, user = await _get_driver_or_404(db, driver_id)
    payload = data or admin_schemas.DriverUnblockRequest()

    if payload.top_up_amount:
        # Balans to'ldirilganda billing o'zi qarz blokini yechadi, lekin qo'lda
        # bloklangan holat uchun quyidagi set_driver_blocked baribir kerak.
        await billing.adjust_user_balance(
            db,
            user,
            amount=payload.top_up_amount,
            note=payload.note or "Admin blokdan chiqarishda balans to'ldirdi",
            admin_id=admin.id,
        )

    if driver.is_blocked:
        await admin_crud.set_driver_blocked(db, driver, blocked=False)

    logger.info(
        "Admin #%s haydovchi #%s ni blokdan chiqardi (balans=%s)", admin.id, driver.id, user.balance
    )
    return _driver_item(driver, user)


@router.post(
    "/drivers/{driver_id}/block",
    response_model=admin_schemas.AdminDriverListItem,
    summary="Haydovchini qo'lda bloklash",
)
async def admin_block_driver(
    driver_id: int,
    data: admin_schemas.DriverBlockRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(is_admin),
):
    driver, user = await _get_driver_or_404(db, driver_id)
    await admin_crud.set_driver_blocked(db, driver, blocked=True, reason=data.reason)
    logger.info("Admin #%s haydovchi #%s ni bloklandi: %s", admin.id, driver.id, data.reason)
    return _driver_item(driver, user)


@router.get(
    "/drivers/monitor",
    response_model=List[admin_schemas.DriverMonitorItem],
    summary="Xarita monitoringi: barcha haydovchilar joylashuvi, holati va joriy yuki",
)
async def admin_drivers_monitor(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
    only_with_location: bool = Query(True, description="Faqat koordinatasi bor haydovchilar"),
):
    """Xarita uchun bitta so'rovda hamma narsa: joylashuv (jonli yoki oxirgi ma'lum),
    onlayn/oflayn, bo'sh/yukli va yukli bo'lsa buyurtma tafsilotlari.

    Joylashuv manbai: avval Redis'dagi jonli translyatsiya (`live`), bo'lmasa DB'dagi
    oxirgi ma'lum nuqta (`last_known` — driver/router.py WS handleri yozadi).
    """
    live_by_driver: dict[int, dict] = {}
    try:
        for entry in await live_location.get_all_online_drivers():
            try:
                live_by_driver[int(entry["driver_id"])] = entry
            except (KeyError, TypeError, ValueError):
                continue
    except Exception:
        logger.exception("Jonli lokatsiyalarni olishda xato (monitor)")

    rows = await admin_crud.list_drivers_for_monitor(db)

    items: List[admin_schemas.DriverMonitorItem] = []
    for driver, user, truck_type_name, order in rows:
        live = live_by_driver.get(driver.id)
        if live:
            latitude, longitude = live.get("lat"), live.get("lon")
            source, located_at = "live", live.get("ts")
        else:
            latitude, longitude = driver.last_latitude, driver.last_longitude
            source = "last_known" if latitude is not None and longitude is not None else None
            located_at = driver.last_location_at

        if only_with_location and (latitude is None or longitude is None):
            continue

        active_order = None
        if order is not None:
            waypoints = list(order.waypoints)
            active_order = admin_schemas.MonitorActiveOrder(
                id=order.id,
                cargo_name=order.cargo_name,
                weight=order.weight,
                volume=order.volume,
                price=order.price,
                currency=order.currency,
                status=order.status.value,
                origin_address=order.origin.address if order.origin else None,
                destination_address=order.destination.address if order.destination else None,
                current_waypoint_address=(
                    order.current_waypoint.address if order.current_waypoint else None
                ),
                total_waypoints=len(waypoints),
                completed_waypoints=sum(
                    1 for wp in waypoints if wp.status.value in ("COMPLETED", "SKIPPED")
                ),
            )

        items.append(
            admin_schemas.DriverMonitorItem(
                driver_id=driver.id,
                user_id=user.id,
                full_name=user.full_name,
                phone_number=user.phone_number,
                truck_type_name=truck_type_name,
                truck_number=driver.truck_number,
                is_available=driver.is_available,
                is_blocked=driver.is_blocked,
                block_reason=driver.block_reason,
                rating=driver.rating,
                total_trips=driver.total_trips,
                online=live is not None,
                busy=order is not None,
                latitude=latitude,
                longitude=longitude,
                location_source=source,
                location_at=located_at,
                active_order=active_order,
            )
        )

    return items


@router.get("/drivers/locations", response_model=List[admin_schemas.DriverLocationItem])
async def admin_list_driver_locations(_: User = Depends(is_admin)):
    items = await live_location.get_all_online_drivers()
    return items


@router.get(
    "/drivers/{driver_id}/location",
    response_model=admin_schemas.DriverLocationItem,
)
async def admin_get_driver_location(
    driver_id: int,
    _: User = Depends(is_admin),
):
    item = await live_location.get_driver_location(driver_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Live lokatsiya yo'q.")
    return item


# DIQQAT: bu marshrut `/drivers/locations` dan KEYIN turishi shart — aks holda "locations"
# so'zi `{driver_id}` sifatida o'qilib, 422 qaytardi.
@router.get(
    "/drivers/{driver_id}",
    response_model=admin_schemas.AdminDriverListItem,
    summary="Bitta haydovchi ma'lumoti (buyurtmaga biriktirishdan oldin tekshirish uchun)",
)
async def admin_get_driver(
    driver_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
):
    driver, user = await _get_driver_or_404(db, driver_id)
    return _driver_item(driver, user)


# ════════════════════════════════════════════════════════════
# KOMISSIYA / BALANS (billing)
# ════════════════════════════════════════════════════════════


@router.get("/settings/commission", response_model=admin_schemas.CommissionSettingsResponse)
async def get_commission_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
):
    return await billing.get_or_create_settings(db)


@router.patch("/settings/commission", response_model=admin_schemas.CommissionSettingsResponse)
async def update_commission_settings(
    data: admin_schemas.CommissionSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
):
    return await billing.update_commission_percent(db, data.commission_percent)


@router.post(
    "/users/{user_id}/balance/adjust",
    response_model=admin_schemas.BalanceTransactionResponse,
    summary="Foydalanuvchi balansini qo'lda o'zgartirish (to'ldirish/tuzatish)",
)
async def adjust_user_balance(
    user_id: int,
    data: admin_schemas.BalanceAdjustRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(is_admin),
):
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")
    return await billing.adjust_user_balance(db, user, amount=data.amount, note=data.note, admin_id=admin.id)


@router.get(
    "/users/{user_id}/balance/transactions",
    response_model=List[admin_schemas.BalanceTransactionResponse],
    summary="Foydalanuvchi balans tarixi",
)
async def list_user_balance_transactions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(is_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    user = await user_crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")
    return await billing.list_balance_transactions(db, user_id, skip=skip, limit=limit)


# --- WebSocket: real-time driver location stream ---


async def _ws_authorize(websocket: WebSocket, token: Optional[str]) -> Optional[User]:
    if not token:
        await websocket.close(code=4401)
        return None

    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4401)
        return None
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4401)
        return None

    async with async_session() as db:
        user = await user_crud.get_user_by_id(db, int(user_id))

    if not user:
        await websocket.close(code=4401)
        return None
    if user.role != UserRole.ADMIN and user.id not in ADMIN_IDS:
        await websocket.close(code=4403)
        return None
    return user


@router.websocket("/drivers/locations/stream")
async def driver_locations_ws(websocket: WebSocket, token: Optional[str] = None):
    user = await _ws_authorize(websocket, token)
    if user is None:
        return

    await websocket.accept()

    try:
        snapshot = await live_location.get_all_online_drivers()
        await websocket.send_text(json.dumps({"event": "snapshot", "items": snapshot}))
    except Exception as exc:
        logger.warning("ws snapshot send failed: %s", exc)

    sub_task = asyncio.create_task(_ws_pump_updates(websocket))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("ws receive error: %s", exc)
    finally:
        sub_task.cancel()


async def _ws_pump_updates(websocket: WebSocket) -> None:
    try:
        async for payload in live_location.subscribe_location_updates():
            try:
                await websocket.send_text(json.dumps({"event": "update", "item": payload}))
            except Exception:
                break
    except asyncio.CancelledError:
        return
    except Exception as exc:
        logger.warning("ws pump error: %s", exc)
