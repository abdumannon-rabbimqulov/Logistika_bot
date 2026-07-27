import logging
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import aiofiles
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from Admin_panel.validation import is_admin
from config.config import (
    LIVE_LOC_DB_THROTTLE_SEC,
    LIVE_LOC_DEFAULT_PERIOD_SEC,
    STATIC_PATH,
    UPLOAD_DIR,
    async_session,
    get_db,
)
from driver import crud, schemas
from driver.models import Driver
from driver.profile import build_driver_profile
from services import billing, live_location
from users import crud as users_crud
from users.auth import get_current_user, verify_token
from users.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drivers", tags=["Haydovchilar (Drivers)"])

LAST_DB_WRITE: dict[int, float] = {}
ORDER_TRACK_INTERVAL_SEC = 600

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB — rasm yuklash uchun maksimal hajm
ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _normalize_ws_token(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    token = raw.strip()
    if token.lower().startswith("bearer "):
        return token[7:].strip()
    return token


@router.post("/truck-types", response_model=schemas.TruckTypeResponse, status_code=status.HTTP_201_CREATED, summary="Yangi mashina turi qo'shish,admin uchun")
async def create_truck_type(
    data: schemas.TruckTypeCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(is_admin),
):
    return await crud.create_truck_type(db, data)

@router.get("/truck-types", response_model=List[schemas.TruckTypeResponse], summary="Barcha mashina turlarini olish,hamma uchun")
async def list_truck_types(db: AsyncSession = Depends(get_db)):
    return await crud.get_all_truck_types(db)

@router.post("/truck-types/image", response_model=dict, summary="Truck type rasmini yuklash, admin uchun")
async def upload_truck_type_image(
    file: UploadFile = File(...),
    admin: User = Depends(is_admin),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Faqat image fayl yuklash mumkin")

    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in ALLOWED_IMAGE_EXTS:
        raise HTTPException(status_code=400, detail="Rasm formati noto'g'ri")

    # Hajm limiti — DoS/disk to'ldirilishining oldini olish uchun cheklab o'qiymiz.
    contents = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fayl juda katta (maks. 5MB)",
        )

    unique_filename = f"truck_type_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    async with aiofiles.open(file_path, "wb") as buffer:
        await buffer.write(contents)

    return {"url": f"{STATIC_PATH}/{unique_filename}"}

@router.get("/truck-types/{pk}", response_model=schemas.TruckTypeResponse, summary="Mashina turi tafsilotlari,hamma uchun")
async def get_truck_type(pk: int, db: AsyncSession = Depends(get_db)):
    obj = await crud.get_truck_type(db, pk)
    if not obj:
        raise HTTPException(status_code=404, detail="Truck type not found")
    return obj

@router.patch("/truck-types/{pk}", response_model=schemas.TruckTypeResponse, summary="Mashina turini tahrirlash,admin uchun")
async def update_truck_type(
    pk: int,
    data: schemas.TruckTypeUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(is_admin),
):
    obj = await crud.update_truck_type(db, pk, data)
    if not obj:
        raise HTTPException(status_code=404, detail="Truck type not found")
    return obj

@router.delete("/truck-types/{pk}", status_code=status.HTTP_204_NO_CONTENT, summary="Mashina turini o'chirish,admin uchun")
async def delete_truck_type(
    pk: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(is_admin),
):
    await crud.delete_truck_type(db, pk)
    return None


@router.post("/profile", response_model=schemas.DriverResponse, status_code=status.HTTP_201_CREATED, summary="Haydovchi profilini yaratish")
async def create_driver_profile(
    data: schemas.DriverCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await crud.get_driver_by_user_id(db, current_user.id)
    if existing:
        raise HTTPException(status_code=400, detail="Driver profile already exists")

    if data.phone_number:
        current_user.phone_number = data.phone_number
        await db.commit()

    return await crud.create_driver(db, data, user_id=current_user.id)

async def _require_driver(db: AsyncSession, current_user: User) -> Driver:
    driver = await crud.get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return driver


@router.get(
    "/me",
    response_model=schemas.DriverProfileResponse,
    summary="Mening haydovchi profilim (kabinet)",
)
@router.get(
    "/profile",
    response_model=schemas.DriverProfileResponse,
    summary="Haydovchi profili — batafsil kabinet ma'lumotlari",
)
async def get_my_driver_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    driver = await _require_driver(db, current_user)
    return await build_driver_profile(db, current_user, driver)


@router.get(
    "/me/balance/transactions",
    response_model=List[schemas.BalanceTransactionItem],
    summary="Mening balans tarixim (komissiya yechilishi va to'ldirishlar)",
)
async def list_my_balance_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Haydovchi kabinetidagi (Profil sahifasi) balans tarixi — faqat o'z yozuvlari."""
    await _require_driver(db, current_user)
    return await billing.list_balance_transactions(db, current_user.id, skip=skip, limit=limit)


@router.patch("/me", response_model=schemas.DriverProfileResponse, summary="Profilni tahrirlash")
async def update_my_driver_profile(
    data: schemas.DriverUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    driver = await _require_driver(db, current_user)

    dump = data.model_dump(exclude_unset=True)
    dump.pop("last_latitude", None)
    dump.pop("last_longitude", None)

    # Bloklangan (masalan qarz tufayli) haydovchi liniyaga chiqa olmaydi
    if driver.is_blocked and (dump.get("is_available") or dump.get("is_live_location_active")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Siz bloklangansiz — liniyaga chiqa olmaysiz. Sababi: " + (driver.block_reason or "noma'lum"),
        )

    if dump:
        await crud.update_driver(db, driver.id, schemas.DriverUpdate(**dump))
        driver = await crud.get_driver(db, driver.id)
    await db.refresh(current_user)
    return await build_driver_profile(db, current_user, driver)




async def _resolve_driver_ws_session(
    token: Optional[str],
) -> Optional[tuple[User, Driver]]:
    """JWT tekshiruvi — WebSocket accept() dan oldin."""
    raw = _normalize_ws_token(token)
    if not raw:
        return None
    payload = verify_token(raw)
    if not payload or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None

    async with async_session() as db:
        user = await users_crud.get_user_by_id(db, int(user_id))
        if not user:
            return None
        driver = await crud.get_driver_by_user_id(db, user.id)
        if not driver or driver.is_blocked:
            return None
        return user, driver


@router.websocket("/ws/location")
async def websocket_driver_location(
    websocket: WebSocket,
    token: Optional[str] = None,
):
    """
    Jonli GPS — faqat WebSocket.
    Token: query `?token=<access_jwt>` (Bearer prefiksi ixtiyoriy).
    Xabarlar: { "latitude": float, "longitude": float } yoki { "event": "stop" }.
    """
    query_token = token or websocket.query_params.get("token")
    session = await _resolve_driver_ws_session(query_token)
    if session is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    user, driver = session
    driver_id = driver.id
    stop_requested = False

    await websocket.accept()
    await websocket.send_json({"status": "connected", "driver_id": driver_id})
    logger.info("Driver %s WS location connected", driver_id)

    try:
        async with async_session() as db:
            while True:
                data = await websocket.receive_json()
                if data.get("event") == "stop":
                    stop_requested = True
                    break

                lat = float(data["latitude"])
                lon = float(data["longitude"])
                # GPS aniqligi (metr) — ixtiyoriy. Geofence tekshiruvida zaxira
                # koordinata ishlatilganda ruxsat etilgan radius shunga qarab kengayadi.
                raw_accuracy = data.get("accuracy")
                accuracy = float(raw_accuracy) if raw_accuracy is not None else None

                await live_location.update_driver_location(
                    driver_id=driver_id,
                    lat=lat,
                    lon=lon,
                    accuracy=accuracy,
                    user_id=user.id,
                    full_name=user.full_name,
                    truck_number=driver.truck_number,
                    truck_type_id=driver.truck_type_id,
                    live_period=1800,
                )

                # Redis'dagi jonli yozuv qisqa umrli (LIVE_LOC_TTL_SEC). Haydovchi
                # ilovani yopgach ham dispatch uni "oxirgi ma'lum joylashuvi" bo'yicha
                # topa olishi uchun koordinata DB'ga ham yoziladi — har xabarda emas,
                # LIVE_LOC_DB_THROTTLE_SEC oralig'ida bir marta (yozuvlar sonini kamaytiradi).
                now_ts = time.monotonic()
                if now_ts - LAST_DB_WRITE.get(driver_id, 0.0) >= LIVE_LOC_DB_THROTTLE_SEC:
                    LAST_DB_WRITE[driver_id] = now_ts
                    await db.execute(
                        update(Driver)
                        .where(Driver.id == driver_id)
                        .values(
                            last_latitude=lat,
                            last_longitude=lon,
                            last_location_at=datetime.now(timezone.utc),
                            is_live_location_active=True,
                            live_location_expires=datetime.now(timezone.utc)
                            + timedelta(seconds=LIVE_LOC_DEFAULT_PERIOD_SEC),
                        )
                    )
                    await db.commit()

                await websocket.send_json({"status": "acknowledged"})

    except WebSocketDisconnect:
        logger.info("Driver %s WS disconnected", driver_id)
    except Exception as exc:
        logger.exception("WS location error: %s", exc)
        try:
            await websocket.close(code=1011, reason="Server error")
        except Exception:
            pass
    finally:
        LAST_DB_WRITE.pop(driver_id, None)
        if stop_requested:
            await live_location.stop_driver_location(driver_id)





