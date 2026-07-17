

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
