import logging
import os
import shutil
import uuid
from typing import List, Optional

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
from sqlalchemy.ext.asyncio import AsyncSession

from Admin_panel.validation import is_admin
from config.config import STATIC_PATH, UPLOAD_DIR, async_session, get_db
from driver import crud, schemas
from driver.models import Driver
from driver.profile import build_driver_profile
from order import crud as order_crud
from order import schemas as order_schemas
from services import live_location
from users import crud as users_crud
from users.auth import get_current_user, verify_token
from users.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/drivers", tags=["Haydovchilar (Drivers)"])

LAST_DB_WRITE: dict[int, float] = {}
ORDER_TRACK_INTERVAL_SEC = 600


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
    if file_ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        raise HTTPException(status_code=400, detail="Rasm formati noto'g'ri")

    unique_filename = f"truck_type_{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"url": f"{STATIC_PATH}/{unique_filename}", "filename": file.filename}

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
    if dump:
        await crud.update_driver(db, driver.id, schemas.DriverUpdate(**dump))
        driver = await crud.get_driver(db, driver.id)
    await db.refresh(current_user)
    return await build_driver_profile(db, current_user, driver)


@router.get(
    "/trips",
    response_model=List[order_schemas.OrderResponse],
    summary="Haydovchi safarlari (buyurtmalar)",
)
async def list_driver_trips(
    response: Response,
    scope: schemas.DriverTripScope = Query(
        schemas.DriverTripScope.ALL,
        description="current — joriy; completed — tugallangan; all — barchasi",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    driver = await _require_driver(db, current_user)
    orders, total = await crud.get_driver_trips(
        db, driver.id, scope=scope.value, skip=skip, limit=limit
    )
    response.headers["X-Total-Count"] = str(total)
    return orders


@router.get(
    "/available-orders",
    response_model=List[order_schemas.OrderResponse],
    summary="Mos keluvchi yangi buyurtmalar (pending, mashina turiga mos)",
)
async def list_available_orders_for_driver(
    limit: int = Query(50, ge=1, le=100),
    relax_truck_match: bool = Query(
        False,
        description="Test: mashina turini filtrlamaslik (yoki RELAX_DRIVER_ORDER_FILTERS=1)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    driver = await _require_driver(db, current_user)
    if driver.is_blocked:
        raise HTTPException(status_code=403, detail="Haydovchi bloklangan")
    relax_env = os.getenv("RELAX_DRIVER_ORDER_FILTERS", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    relax = relax_truck_match or relax_env
    return await order_crud.get_available_orders_for_driver(
        db, driver.truck_type_id, limit=limit, relax_truck=relax
    )




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

                await live_location.update_driver_location(
                    driver_id=driver_id,
                    lat=lat,
                    lon=lon,
                    user_id=user.id,
                    full_name=user.full_name,
                    truck_number=driver.truck_number,
                    truck_type_id=driver.truck_type_id,
                    live_period=1800,
                )
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





