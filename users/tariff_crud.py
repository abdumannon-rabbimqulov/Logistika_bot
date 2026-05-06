from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from users.models import UserTariffPayment
from users.schemas import UserTariffPaymentCreate, UserTariffPaymentUpdate


def billing_month_date(year: int, month: int) -> date:
    return date(year, month, 1)


async def create_tariff_payment(
    db: AsyncSession,
    data: UserTariffPaymentCreate,
    *,
    recorded_by_admin_id: int,
) -> UserTariffPayment:
    row = UserTariffPayment(
        user_id=data.user_id,
        billing_month=billing_month_date(data.billing_year, data.billing_month),
        amount=data.amount,
        currency=data.currency,
        tariff_code=data.tariff_code,
        paid_at=data.paid_at,
        note=data.note,
        recorded_by_admin_id=recorded_by_admin_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def get_tariff_payment(db: AsyncSession, pk: int) -> Optional[UserTariffPayment]:
    result = await db.execute(select(UserTariffPayment).where(UserTariffPayment.id == pk))
    return result.scalar_one_or_none()


async def list_tariff_payments_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    year: Optional[int] = None,
) -> List[UserTariffPayment]:
    stmt = select(UserTariffPayment).where(UserTariffPayment.user_id == user_id)
    if year is not None:
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
        stmt = stmt.where(UserTariffPayment.billing_month >= start, UserTariffPayment.billing_month < end)
    stmt = stmt.order_by(UserTariffPayment.billing_month.desc(), UserTariffPayment.id.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_all_tariff_payments(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
) -> List[UserTariffPayment]:
    stmt = select(UserTariffPayment)
    if user_id is not None:
        stmt = stmt.where(UserTariffPayment.user_id == user_id)
    stmt = stmt.order_by(UserTariffPayment.billing_month.desc(), UserTariffPayment.id.desc())
    stmt = stmt.offset(max(skip, 0)).limit(min(max(limit, 1), 500))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_tariff_payment(
    db: AsyncSession,
    row: UserTariffPayment,
    data: UserTariffPaymentUpdate,
) -> UserTariffPayment:
    payload = data.model_dump(exclude_unset=True)
    if payload:
        ym = payload.pop("billing_year", None)
        mm = payload.pop("billing_month", None)
        if ym is not None or mm is not None:
            y = ym if ym is not None else row.billing_month.year
            m = mm if mm is not None else row.billing_month.month
            row.billing_month = billing_month_date(y, m)
        for k, v in payload.items():
            setattr(row, k, v)
    await db.commit()
    await db.refresh(row)
    return row


async def delete_tariff_payment(db: AsyncSession, row: UserTariffPayment) -> None:
    await db.delete(row)
    await db.commit()


async def monthly_totals_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    year: int,
) -> List[tuple]:
    """(billing_month, total_amount Decimal, payment_count int, currency) ro'yxati."""
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)

    stmt = (
        select(
            UserTariffPayment.billing_month,
            func.coalesce(func.sum(UserTariffPayment.amount), Decimal("0")),
            func.count(UserTariffPayment.id),
            UserTariffPayment.currency,
        )
        .where(
            UserTariffPayment.user_id == user_id,
            UserTariffPayment.billing_month >= start,
            UserTariffPayment.billing_month < end,
        )
        .group_by(UserTariffPayment.billing_month, UserTariffPayment.currency)
        .order_by(UserTariffPayment.billing_month.asc())
    )
    result = await db.execute(stmt)
    return [(r[0], r[1], r[2], r[3]) for r in result.all()]
