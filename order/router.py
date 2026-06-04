from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from config.config import get_db
from order import crud, schemas
from order.models import OrderStatus
from users.auth import get_current_user
from users.models import User, UserRole

router = APIRouter(prefix="/orders", tags=["Buyurtmalar (Orders)"])


# --- Order Endpoints ---

@router.post("/", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED, summary="Yangi buyurtma yaratish")
async def create_order(
    data: schemas.OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mijoz tomonidan yangi yuk tashish buyurtmasini shakllantirish.

    `customer_id` JWT tokendan olinadi — clientdan talab qilinmaydi.
    """
    return await crud.create_order(db, data, customer_id=current_user.id)

@router.get("/", response_model=List[schemas.OrderResponse], summary="Barcha buyurtmalar ro'yxati")
async def list_orders(
    customer_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    status: Optional[str] = None,
    required_truck_type_id: Optional[int] = Query(
        None, description="Mashina turi bo'yicha filtr (haydovchi uchun)"
    ),
    unassigned_only: bool = Query(
        False, description="Faqat haydovchisiz buyurtmalar (driver_id IS NULL)"
    ),
    filter_by_truck: bool = Query(
        False,
        description="Haydovchi uchun: faqat o'z mashina turiga mos buyurtmalar (required_truck_type_id)",
    ),
    match_my_truck: bool = Query(
        False,
        description="(Eski) filter_by_truck=true bilan bir xil",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tizimdagi yuk buyurtmalari. Waypoints sequence bo'yicha tartiblangan."""
    from driver.crud import get_driver_by_user_id

    parsed_status = crud.parse_order_status(status)
    apply_truck_filter = filter_by_truck or match_my_truck

    # Haydovchi bozori — admin bilan bir xil `orders` jadvali, enum status + driver_id IS NULL
    is_driver_marketplace = (
        current_user.role == UserRole.DRIVER
        and customer_id is None
        and driver_id is None
    )
    if is_driver_marketplace:
        driver = await get_driver_by_user_id(db, current_user.id)
        truck_filter_id: Optional[int] = None
        if apply_truck_filter:
            if not driver:
                raise HTTPException(
                    status_code=403,
                    detail="Haydovchi profili topilmadi — mashina turiga filtrlash mumkin emas",
                )
            if driver.is_blocked:
                raise HTTPException(status_code=403, detail="Haydovchi bloklangan")
            truck_filter_id = driver.truck_type_id

        marketplace_status = parsed_status or OrderStatus.PENDING
        return await crud.list_driver_marketplace_orders(
            db,
            status=marketplace_status,
            truck_type_id=truck_filter_id,
        )

    # Mijoz / boshqa rollar
    truck_type_id = required_truck_type_id
    only_unassigned = unassigned_only

    if apply_truck_filter:
        driver = await get_driver_by_user_id(db, current_user.id)
        if not driver:
            raise HTTPException(
                status_code=403,
                detail="Haydovchi profili topilmadi — mashina turiga filtrlash mumkin emas",
            )
        if driver.is_blocked:
            raise HTTPException(status_code=403, detail="Haydovchi bloklangan")
        truck_type_id = driver.truck_type_id

    if match_my_truck:
        only_unassigned = True

    return await crud.get_all_orders(
        db,
        customer_id,
        driver_id,
        status,
        required_truck_type_id=truck_type_id,
        unassigned_only=only_unassigned,
    )

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
