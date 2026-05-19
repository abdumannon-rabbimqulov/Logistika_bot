import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from config.config import STATIC_PATH, UPLOAD_DIR, get_db
from driver import crud, schemas
from users.auth import get_current_user
from users.models import User
from Admin_panel.validation import is_admin

router = APIRouter(prefix="/drivers", tags=["Haydovchilar (Drivers)"])


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
    return await crud.update_driver(db, driver.id, data)







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