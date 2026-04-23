from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

import crud
from config.config import get_db
from models import OfferStatus, OrderStatus
from schemas import (
    OrderCreate, OrderOfferCreate, OrderOfferRead, OrderOfferStatusUpdate,
    OrderOfferUpdate, OrderRead, OrderReadWithOffers, OrderStatusUpdate,
    OrderUpdate,
)

router = APIRouter()


async def _get_order_or_404(order_id: int, db: AsyncSession):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} topilmadi.",
        )
    return order


async def _get_offer_or_404(offer_id: int, db: AsyncSession):
    offer = await crud.get_offer(db, offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Offer {offer_id} topilmadi.",
        )
    return offer



@router.post(
    "/orders",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi buyurtma yaratish",
    tags=["Orders"],
)
async def create_order(
    data: OrderCreate,
    customer_id: int = Query(..., description="Buyurtmachi ID (auth dan olinadi)"),
    db: AsyncSession = Depends(get_db),
):
    return await crud.create_order(db, customer_id=customer_id, data=data)


@router.get(
    "/orders",
    response_model=list[OrderRead],
    summary="Barcha buyurtmalarni olish (filter bilan)",
    tags=["Orders"],
)
async def list_orders(
    customer_id: Optional[int] = Query(None),
    driver_id: Optional[int] = Query(None),
    status: Optional[OrderStatus] = Query(None),
    from_city: Optional[str] = Query(None),
    to_city: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_orders(
        db,
        customer_id=customer_id,
        driver_id=driver_id,
        status=status,
        from_city=from_city,
        to_city=to_city,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/orders/{order_id}",
    response_model=OrderReadWithOffers,
    summary="Buyurtma ma'lumotlarini olish (offerlar bilan)",
    tags=["Orders"],
)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    order = await crud.get_order(db, order_id, with_offers=True)
    if not order:
        raise HTTPException(status_code=404, detail="Order topilmadi.")
    return order


@router.patch(
    "/orders/{order_id}",
    response_model=OrderRead,
    summary="Buyurtmani tahrirlash",
    tags=["Orders"],
)
async def update_order(
    order_id: int,
    data: OrderUpdate,
    db: AsyncSession = Depends(get_db),
):
    order = await _get_order_or_404(order_id, db)
    return await crud.update_order(db, order, data)


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderRead,
    summary="Buyurtma statusini o'zgartirish",
    tags=["Orders"],
)
async def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    order = await _get_order_or_404(order_id, db)
    return await crud.update_order_status(db, order, data.status)


@router.patch(
    "/orders/{order_id}/assign-driver",
    response_model=OrderRead,
    summary="Drayver tayinlash",
    tags=["Orders"],
)
async def assign_driver(
    order_id: int,
    driver_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    order = await _get_order_or_404(order_id, db)
    return await crud.assign_driver_to_order(db, order, driver_id)


@router.delete(
    "/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Buyurtmani o'chirish",
    tags=["Orders"],
)
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
):
    order = await _get_order_or_404(order_id, db)
    await crud.delete_order(db, order)



@router.post(
    "/orders/{order_id}/offers",
    response_model=OrderOfferRead,
    status_code=status.HTTP_201_CREATED,
    summary="Buyurtmaga offer yuborish",
    tags=["Offers"],
)
async def create_offer(
    order_id: int,
    data: OrderOfferCreate,
    driver_id: int = Query(..., description="Driver ID (auth dan olinadi)"),
    db: AsyncSession = Depends(get_db),
):
    await _get_order_or_404(order_id, db)
    return await crud.create_offer(db, order_id=order_id, driver_id=driver_id, data=data)


@router.get(
    "/orders/{order_id}/offers",
    response_model=list[OrderOfferRead],
    summary="Buyurtmadagi barcha offerlarni olish",
    tags=["Offers"],
)
async def list_offers_for_order(
    order_id: int,
    offer_status: Optional[OfferStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    await _get_order_or_404(order_id, db)
    return await crud.get_offers_for_order(db, order_id, status=offer_status)


@router.get(
    "/drivers/{driver_id}/offers",
    response_model=list[OrderOfferRead],
    summary="Driver yuborgan barcha offerlar",
    tags=["Offers"],
)
async def list_offers_by_driver(
    driver_id: int,
    offer_status: Optional[OfferStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_offers_by_driver(
        db, driver_id, status=offer_status, skip=skip, limit=limit
    )


@router.get(
    "/offers/{offer_id}",
    response_model=OrderOfferRead,
    summary="Offer ma'lumotlarini olish",
    tags=["Offers"],
)
async def get_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await _get_offer_or_404(offer_id, db)


@router.patch(
    "/offers/{offer_id}",
    response_model=OrderOfferRead,
    summary="Offerni tahrirlash",
    tags=["Offers"],
)
async def update_offer(
    offer_id: int,
    data: OrderOfferUpdate,
    db: AsyncSession = Depends(get_db),
):
    offer = await _get_offer_or_404(offer_id, db)
    return await crud.update_offer(db, offer, data)


@router.patch(
    "/offers/{offer_id}/status",
    response_model=OrderOfferRead,
    summary="Offer statusini o'zgartirish",
    tags=["Offers"],
)
async def update_offer_status(
    offer_id: int,
    data: OrderOfferStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    offer = await _get_offer_or_404(offer_id, db)
    return await crud.update_offer_status(db, offer, data.status)


@router.post(
    "/offers/{offer_id}/accept",
    response_model=OrderOfferRead,
    summary="Offerni qabul qilish (boshqalari avtomatik REJECTED bo'ladi)",
    tags=["Offers"],
)
async def accept_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
):
    offer = await _get_offer_or_404(offer_id, db)
    if offer.status != OfferStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Faqat PENDING statusdagi offer qabul qilinishi mumkin. Hozirgi: {offer.status.value}",
        )
    accepted_offer, _ = await crud.accept_offer(db, offer)
    return accepted_offer


@router.delete(
    "/offers/{offer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Offerni o'chirish",
    tags=["Offers"],
)
async def delete_offer(
    offer_id: int,
    db: AsyncSession = Depends(get_db),
):
    offer = await _get_offer_or_404(offer_id, db)
    await crud.delete_offer(db, offer)