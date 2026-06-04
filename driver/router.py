import logging
import os
import shutil
import time
import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from Admin_panel.validation import is_admin
from config.config import STATIC_PATH, UPLOAD_DIR, async_session, get_db
from driver import crud, schemas
from driver.models import Driver
from order.models import Order, OrderStatus, OrderTrack
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

@router.get("/me", response_model=schemas.DriverResponse, summary="Mening haydovchi profilim")
async def get_my_driver_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    obj = await crud.get_driver_by_user_id(db, current_user.id)
    if not obj:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    return obj

@router.patch("/me", response_model=schemas.DriverResponse, summary="Profilni tahrirlash")
async def update_my_driver_profile(
    data: schemas.DriverUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    driver = await crud.get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    dump = data.model_dump(exclude_unset=True)
    dump.pop("last_latitude", None)
    dump.pop("last_longitude", None)
    if dump:
        updated = await crud.update_driver(db, driver.id, schemas.DriverUpdate(**dump))
        return updated
    return await crud.get_driver(db, driver.id)


async def _save_order_track_if_needed(
    db: AsyncSession, driver_id: int, lat: float, lon: float
) -> None:
    """IN_PROGRESS buyurtma bo'lsa har 10 daqiqada OrderTrack."""
    now = time.time()
    last = LAST_DB_WRITE.get(driver_id, 0)
    if now - last < ORDER_TRACK_INTERVAL_SEC:
        return

    result = await db.execute(
        select(Order).where(
            Order.driver_id == driver_id,
            Order.status == OrderStatus.IN_PROGRESS,
        )
    )
    active_order = result.scalar_one_or_none()
    if not active_order:
        return

    db.add(
        OrderTrack(
            order_id=active_order.id,
            latitude=lat,
            longitude=lon,
        )
    )
    await db.commit()
    LAST_DB_WRITE[driver_id] = now
    logger.info("OrderTrack #%s driver=%s", active_order.id, driver_id)


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
                await _save_order_track_if_needed(db, driver_id, lat, lon)
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





@router.post("/announcements", response_model=schemas.DriverAnnouncementResponse, status_code=status.HTTP_201_CREATED, summary="Safar e'loni berish")
async def create_announcement(
    data: schemas.DriverAnnouncementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    driver = await crud.get_driver(db, data.driver_id)
    if not driver or driver.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return await crud.create_announcement(db, data)

@router.get("/announcements", response_model=List[schemas.DriverAnnouncementResponse], summary="E'lonlar ro'yxati")
async def list_announcements(
    driver_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await crud.get_all_announcements(db, driver_id)

@router.get("/announcements/{pk}", response_model=schemas.DriverAnnouncementResponse, summary="E'lon tafsilotlari")
async def get_announcement(
    pk: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    obj = await crud.get_announcement(db, pk)
    if not obj:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return obj


@router.post("/announcements/{announcement_id}/offers", response_model=schemas.AnnouncementOfferResponse, status_code=status.HTTP_201_CREATED, summary="E'longa taklif berish")
async def make_offer_on_announcement(
    announcement_id: int,
    data: schemas.AnnouncementOfferBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offer_data = schemas.AnnouncementOfferCreate(
        announcement_id=announcement_id,
        customer_id=current_user.id,
        **data.model_dump()
    )
    return await crud.create_announcement_offer(db, offer_data)

@router.get("/announcements/{announcement_id}/offers", response_model=List[schemas.AnnouncementOfferResponse], summary="E'longa kelgan takliflar")
async def list_offers_on_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    announcement = await crud.get_announcement(db, announcement_id)
    if not announcement:
        raise HTTPException(status_code=404, detail="E'lon topilmadi")
    
    driver = await crud.get_driver_by_user_id(db, current_user.id)
    if not driver or announcement.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="Sizga ushbu e'lon takliflarini ko'rish ruxsat etilmagan")

    return await crud.get_announcement_offers(db, announcement_id)

@router.patch("/offers/{pk}", response_model=schemas.AnnouncementOfferResponse, summary="Taklifni yangilash")
async def update_offer(
    pk: int,
    data: schemas.AnnouncementOfferUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offer = await crud.get_announcement_offer(db, pk)
    if not offer:
        raise HTTPException(status_code=404, detail="Taklif topilmadi")
    
    announcement = await crud.get_announcement(db, offer.announcement_id)
    driver = await crud.get_driver_by_user_id(db, current_user.id)
    
    if not driver or announcement.driver_id != driver.id:
          raise HTTPException(status_code=403, detail="Ruxsat berilmagan")

    return await crud.update_announcement_offer(db, pk, data)