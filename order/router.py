from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from config.config import get_db
from order import crud, schemas
from users.auth import get_current_user
from users.models import User

router = APIRouter(prefix="/orders", tags=["Buyurtmalar (Orders)"])

# --- Order Endpoints ---

@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED, summary="Yangi buyurtma yaratish")
async def create_order(
    data: schemas.OrderCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mijoz tomonidan yangi yuk tashish buyurtmasini shakllantirish."""
    if data.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return await crud.create_order(db, data)

@router.get("/", response_model=List[schemas.OrderResponse], summary="Barcha buyurtmalar ro'yxati")
async def list_orders(
    customer_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tizimdagi barcha yuk buyurtmalarini ko'rish. Filtrlar mavjud."""
    return await crud.get_all_orders(db, customer_id, driver_id, status)

@router.get("/{pk}", response_model=schemas.OrderResponse, summary="Buyurtma tafsilotlari")
async def get_order(
    pk: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bitta buyurtma haqida barcha ma'lumotlarni ko'rish."""
    obj = await crud.get_order(db, pk)
    if not obj:
        raise HTTPException(status_code=404, detail="Order not found")
    return obj

@router.patch("/{pk}", response_model=schemas.OrderResponse, summary="Buyurtmani tahrirlash")
async def update_order(
    pk: int, 
    data: schemas.OrderUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Buyurtma ma'lumotlarini yoki statusini yangilash."""
    order = await crud.get_order(db, pk)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Simple check: only owner can update general info
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    return await crud.update_order(db, pk, data)

@router.delete("/{pk}", status_code=status.HTTP_204_NO_CONTENT, summary="Buyurtmani o'chirish")
async def delete_order(
    pk: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Buyurtmani tizimdan o'chirish."""
    order = await crud.get_order(db, pk)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    await crud.delete_order(db, pk)
    return None

# --- OrderOffer Endpoints ---

@router.post("/{order_id}/offers", response_model=schemas.OrderOfferResponse, status_code=status.HTTP_201_CREATED, summary="Buyurtmaga taklif berish")
async def create_offer(
    order_id: int,
    data: schemas.OrderOfferBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Haydovchi mijozning buyurtmasiga o'z narxini taklif qilishi."""
    # Logic to check if user is a driver should be added
    from driver.crud import get_driver_by_user_id
    driver = await get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(status_code=403, detail="Only drivers can make offers")
        
    offer_create = schemas.OrderOfferCreate(
        order_id=order_id,
        driver_id=driver.id,
        **data.model_dump()
    )
    return await crud.create_order_offer(db, offer_create)

@router.get("/{order_id}/offers", response_model=List[schemas.OrderOfferResponse], summary="Buyurtmaga kelgan takliflar")
async def list_order_offers(
    order_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ma'lum bir yuk uchun kelgan barcha takliflarni ko'rish."""
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Check if user is the owner of the order
    if order.customer_id != current_user.id:
        raise HTTPException(status_code=403, detail="Sizga ushbu buyurtma takliflarini ko'rish ruxsat etilmagan")

    return await crud.get_order_offers(db, order_id)

@router.patch("/offers/{pk}", response_model=schemas.OrderOfferResponse, summary="Taklifni yangilash")
async def update_offer(
    pk: int,
    data: schemas.OrderOfferUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Taklifni qabul qilish yoki rad etish."""
    offer = await crud.get_order_offer(db, pk)
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    # Permissions check
    return await crud.update_order_offer(db, pk, data)
