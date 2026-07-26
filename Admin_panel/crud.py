
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import desc, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from driver.models import Driver
from order.models import Order, OrderStatus
from users.models import User, UserRole
from Admin_panel.schemas import (
    AdminDashboardStats,
    AdminUserUpdate,
    AdminOrderUpdate,
    OrdersByDay,
)
from utils.validation import normalize_phone_number


# ════════════════════════════════════════════════════════════
# USERS
# ════════════════════════════════════════════════════════════


async def list_users(
    db: AsyncSession,
    *,
    role: Optional[UserRole] = None,
    is_banned: Optional[bool] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[User], int]:
    base = select(User)
    if role is not None:
        base = base.where(User.role == role)
    if is_banned is not None:
        base = base.where(User.is_banned == is_banned)
    if is_active is not None:
        base = base.where(User.is_active == is_active)
    if search:
        cleaned_search = search.strip()
        like = f"%{cleaned_search}%"
        
        phone_conditions = []
        digits = "".join(c for c in cleaned_search if c.isdigit())
        if digits:
            try:
                norm_phone = normalize_phone_number(cleaned_search)
                plus_less = norm_phone.lstrip('+')
                phone_conditions.extend([
                    User.phone_number.ilike(f"%{norm_phone}%"),
                    User.phone_number.ilike(f"%{plus_less}%")
                ])
            except Exception:
                phone_conditions.append(User.phone_number.ilike(f"%{digits}%"))
                if not cleaned_search.startswith("+"):
                    phone_conditions.append(User.phone_number.ilike(f"%+{digits}%"))
        else:
            phone_conditions.append(User.phone_number.ilike(like))

        base = base.where(
            or_(
                User.full_name.ilike(like),
                User.username.ilike(like),
                User.email.ilike(like),
                *phone_conditions
            )
        )

    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = (
        base.order_by(desc(User.created_at))
        .offset(max(skip, 0))
        .limit(min(max(limit, 1), 200))
    )

    result = await db.execute(stmt)
    rows = result.scalars().unique().all()
    return list(rows), int(total)


async def update_user_admin(db: AsyncSession, user: User, data: AdminUserUpdate) -> User:
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return user


# ════════════════════════════════════════════════════════════
# ORDERS
# ════════════════════════════════════════════════════════════



async def list_orders_admin(
    db: AsyncSession,
    *,
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Order], int]:
    """Admin buyurtmalar ro'yxati (filtrlar + sahifalash). (rows, total) qaytaradi.

    `waypoints` selectinload bilan oldindan yuklanadi — OrderResponse serializatsiyasi
    (waypoints ro'yxatini o'z ichiga oladi) async lazy-load xatosiga uchramasligi uchun.
    """
    base = select(Order)
    if status:
        # OrderStatus enum qiymati ("PENDING" ...). Kichik/aralash harf bilan kelsa ham
        # qabul qilamiz. Yaroqsiz qiymatda xom satrni enum ustuniga bind qilib bo'lmaydi —
        # SQLAlchemy execute paytida LookupError tashlaydi (500). Shu sabab ochiqcha
        # "hech nima mos kelmasin" sharti qo'yiladi va bo'sh natija qaytadi.
        try:
            base = base.where(Order.status == OrderStatus(status.upper()))
        except ValueError:
            base = base.where(false())
    if customer_id is not None:
        base = base.where(Order.customer_id == customer_id)
    if driver_id is not None:
        base = base.where(Order.driver_id == driver_id)
    if date_from is not None:
        base = base.where(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to is not None:
        base = base.where(Order.created_at <= datetime.combine(date_to, datetime.max.time()))

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    stmt = (
        base.options(selectinload(Order.waypoints))
        .order_by(desc(Order.created_at))
        .offset(max(skip, 0))
        .limit(min(max(limit, 1), 200))
    )
    rows = (await db.execute(stmt)).scalars().unique().all()
    return list(rows), int(total)


async def update_order_admin(db: AsyncSession, order: Order, data: AdminOrderUpdate) -> Order:
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(order, k, v)
    await db.commit()
    await db.refresh(order)
    return order


# ════════════════════════════════════════════════════════════
# DASHBOARD STATS
# ════════════════════════════════════════════════════════════


async def dashboard_stats(db: AsyncSession) -> AdminDashboardStats:
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    seven_days_ago = today - timedelta(days=6)

    users_total = (await db.execute(select(func.count(User.id)))).scalar_one()
    users_today = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at.between(today_start, today_end))
        )
    ).scalar_one()

    drivers_total = (await db.execute(select(func.count(Driver.id)))).scalar_one()
    drivers_online = (
        await db.execute(select(func.count(Driver.id)).where(Driver.is_available == True))  # noqa: E712
    ).scalar_one()
    drivers_live_gps = (
        await db.execute(
            select(func.count(Driver.id)).where(Driver.is_live_location_active == True)  # noqa: E712
        )
    ).scalar_one()

    orders_total = (await db.execute(select(func.count(Order.id)))).scalar_one()
    orders_today = (
        await db.execute(
            select(func.count(Order.id)).where(Order.created_at.between(today_start, today_end))
        )
    ).scalar_one()

    # Umumiy aylanma — DB tomonda SUM bilan. Buni frontendda sahifalangan ro'yxatni
    # qo'shib hisoblab bo'lmaydi: /system/orders limiti 200 ta bilan cheklangan.
    revenue_total = (
        await db.execute(
            select(func.coalesce(func.sum(Order.price), 0)).where(
                Order.status == OrderStatus.COMPLETED
            )
        )
    ).scalar_one()

    by_status_rows = (
        await db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status))
    ).all()
    orders_by_status = {
        (s.value if hasattr(s, "value") else str(s)): int(c) for s, c in by_status_rows
    }


    by_day_rows = (
        await db.execute(
            select(
                func.date(Order.created_at).label("d"),
                func.count(Order.id),
            )
            .where(Order.created_at >= datetime.combine(seven_days_ago, datetime.min.time()))
            .group_by(func.date(Order.created_at))
            .order_by(func.date(Order.created_at))
        )
    ).all()
    by_day_map = {r[0]: int(r[1]) for r in by_day_rows}
    last_7 = []
    for i in range(7):
        d = seven_days_ago + timedelta(days=i)
        last_7.append(OrdersByDay(date=d, count=by_day_map.get(d, 0)))

    return AdminDashboardStats(
        users_total=int(users_total),
        users_today=int(users_today),
        drivers_total=int(drivers_total),
        drivers_online=int(drivers_online),
        drivers_live_gps=int(drivers_live_gps),
        orders_total=int(orders_total),
        orders_today=int(orders_today),
        revenue_total=Decimal(str(revenue_total or 0)),
        orders_by_status=orders_by_status,
        orders_last_7_days=last_7,
    )
