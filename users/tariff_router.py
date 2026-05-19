
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import get_db
from users.auth import get_current_admin
from users.crud import get_user_by_id
from users.models import User
from users import schemas as user_schemas
from users import tariff_crud


router = APIRouter(prefix="/system/tariffs", tags=["Admin — tarif/to‘lov"])


@router.post(
    "/payments",
    response_model=user_schemas.UserTariffPaymentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Oylik to‘lov yozuvi qo‘shish",
)
async def admin_create_tariff_payment(
    data: user_schemas.UserTariffPaymentCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    user = await get_user_by_id(db, data.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Foydalanuvchi #{data.user_id} topilmadi.",
        )
    row = await tariff_crud.create_tariff_payment(
        db,
        data,
        recorded_by_admin_id=admin.id,
    )
    return row


@router.get("/payments/all", response_model=List[user_schemas.UserTariffPaymentRead])
async def admin_list_all_payments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
    user_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    return await tariff_crud.list_all_tariff_payments(
        db, skip=skip, limit=limit, user_id=user_id
    )


@router.get("/payments/{payment_id}", response_model=user_schemas.UserTariffPaymentRead)
async def admin_get_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    row = await tariff_crud.get_tariff_payment(db, payment_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Yozuv topilmadi.")
    return row


@router.patch("/payments/{payment_id}", response_model=user_schemas.UserTariffPaymentRead)
async def admin_update_payment(
    payment_id: int,
    data: user_schemas.UserTariffPaymentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    row = await tariff_crud.get_tariff_payment(db, payment_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Yozuv topilmadi.")
    return await tariff_crud.update_tariff_payment(db, row, data)


@router.delete("/payments/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_payment(
    payment_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    row = await tariff_crud.get_tariff_payment(db, payment_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Yozuv topilmadi.")
    await tariff_crud.delete_tariff_payment(db, row)


@router.get(
    "/users/{user_id}/payments",
    response_model=List[user_schemas.UserTariffPaymentRead],
    summary="Bitta userning barcha to‘lov yozuvlari",
)
async def admin_list_user_payments(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
    year: Optional[int] = Query(None, description="Filtr — faqat bu yilda"),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")
    return await tariff_crud.list_tariff_payments_for_user(db, user_id, year=year)


@router.get(
    "/users/{user_id}/summary",
    response_model=List[user_schemas.UserMonthlyTariffSummary],
    summary="Yil bo‘yicha oyma-oy yig‘indilar",
)
async def admin_user_monthly_summary(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_admin),
    year: int = Query(..., ge=2000, le=2100, description="Masalan 2026"),
):
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Foydalanuvchi topilmadi.")
    rows = await tariff_crud.monthly_totals_for_user(db, user_id, year=year)
    return [
        user_schemas.UserMonthlyTariffSummary(
            billing_month=bm,
            total_amount=total,
            payment_count=cnt,
            currency=curr,
        )
        for bm, total, cnt, curr in rows
    ]
