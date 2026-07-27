"""Komissiya hisob-kitobi va haydovchi balansini boshqarish.

Biznes qoidasi: har bir muvaffaqiyatli yakunlangan (COMPLETED) order uchun
tizim komissiyasi haydovchi balansidan avtomatik yechiladi. Komissiya foizini
admin belgilaydi (`PlatformSettings.commission_percent`). Balans manfiy
bo'lib qolsa (qarz), haydovchi avtomatik bloklanadi — bloklangan haydovchi
liniyaga chiqa olmaydi va order qabul qila olmaydi (tekshiruv driver/router.py
va order/router.py'da amalga oshirilgan).
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from Admin_panel.models import PlatformSettings
from driver.models import Driver
from order.models import Order
from users.models import BalanceTransaction, BalanceTransactionType, User

logger = logging.getLogger(__name__)

DEFAULT_COMMISSION_PERCENT = Decimal("10.00")

# Auto-bloklangan haydovchini admin balans to'ldirganda avtomatik blokdan chiqarish
# uchun shu matn bilan belgilanadi (qo'lda bloklangan holatlarni chalkashtirmaslik uchun).
DEBT_BLOCK_REASON = "Balans manfiy (qarz) — tizim tomonidan avtomatik bloklangan"


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def get_or_create_settings(db: AsyncSession) -> PlatformSettings:
    result = await db.execute(select(PlatformSettings).where(PlatformSettings.id == 1))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = PlatformSettings(id=1, commission_percent=DEFAULT_COMMISSION_PERCENT)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


async def update_commission_percent(db: AsyncSession, percent: Decimal) -> PlatformSettings:
    settings = await get_or_create_settings(db)
    settings.commission_percent = percent
    await db.commit()
    await db.refresh(settings)
    return settings


async def update_sender_max_discount_percent(db: AsyncSession, percent: Decimal) -> PlatformSettings:
    """SENDER_MAX_DISCOUNT_PERCENT — sender narxni qo'lda qancha tushira olishi (services/pricing.py)."""
    settings = await get_or_create_settings(db)
    settings.sender_max_discount_percent = percent
    await db.commit()
    await db.refresh(settings)
    return settings


async def _block_driver_for_debt(db: AsyncSession, driver: Driver) -> None:
    driver.is_blocked = True
    driver.block_reason = DEBT_BLOCK_REASON
    driver.is_available = False
    await db.commit()


async def charge_order_commission(db: AsyncSession, order: Order) -> Optional[BalanceTransaction]:
    """COMPLETED bo'lgan order uchun haydovchi balansidan komissiya yechadi.

    Order haydovchisiz bo'lsa hech narsa qilinmaydi (None qaytadi).
    """
    if order.driver_id is None:
        return None

    driver_result = await db.execute(select(Driver).where(Driver.id == order.driver_id))
    driver = driver_result.scalar_one_or_none()
    if driver is None:
        logger.warning("Order #%s uchun driver_id=%s topilmadi — komissiya yechilmadi", order.id, order.driver_id)
        return None

    user_result = await db.execute(select(User).where(User.id == driver.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        logger.error("Driver #%s uchun User(id=%s) topilmadi — komissiya yechilmadi", driver.id, driver.user_id)
        return None

    settings = await get_or_create_settings(db)
    commission_amount = _round(order.price * settings.commission_percent / Decimal("100"))

    new_balance = _round(Decimal(user.balance or 0) - commission_amount)
    user.balance = new_balance

    transaction = BalanceTransaction(
        user_id=user.id,
        type=BalanceTransactionType.ORDER_COMMISSION,
        amount=-commission_amount,
        balance_after=new_balance,
        order_id=order.id,
        note=f"Buyurtma #{order.id} komissiyasi ({settings.commission_percent}%)",
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)

    if new_balance < 0 and not driver.is_blocked:
        await _block_driver_for_debt(db, driver)
        logger.info("Driver #%s qarzga kirdi (balans=%s) — avtomatik bloklandi", driver.id, new_balance)

    return transaction


async def adjust_user_balance(
    db: AsyncSession,
    user: User,
    *,
    amount: Decimal,
    note: Optional[str],
    admin_id: int,
) -> BalanceTransaction:
    """Admin tomonidan qo'lda balans o'zgartirish (musbat = to'ldirish, manfiy = tuzatish/yechish).

    Agar bu foydalanuvchi haydovchi bo'lsa va yangi balans >= 0 bo'lsa, avval qarz
    tufayli avtomatik bloklangan bo'lsa — blokdan chiqariladi.
    """
    new_balance = _round(Decimal(user.balance or 0) + amount)
    user.balance = new_balance

    transaction = BalanceTransaction(
        user_id=user.id,
        type=BalanceTransactionType.ADMIN_ADJUSTMENT,
        amount=_round(amount),
        balance_after=new_balance,
        note=note,
        created_by_admin_id=admin_id,
    )
    db.add(transaction)

    if new_balance >= 0:
        driver_result = await db.execute(select(Driver).where(Driver.user_id == user.id))
        driver = driver_result.scalar_one_or_none()
        if driver and driver.is_blocked and driver.block_reason == DEBT_BLOCK_REASON:
            driver.is_blocked = False
            driver.block_reason = None

    await db.commit()
    await db.refresh(transaction)
    return transaction


async def list_balance_transactions(db: AsyncSession, user_id: int, *, skip: int = 0, limit: int = 50):
    result = await db.execute(
        select(BalanceTransaction)
        .where(BalanceTransaction.user_id == user_id)
        .order_by(BalanceTransaction.created_at.desc())
        .offset(max(skip, 0))
        .limit(min(max(limit, 1), 200))
    )
    return result.scalars().all()
