"""Admin paneli uchun maxsus CRUD funktsiyalari (users, orders, stats, ai_commands)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ai.models import AICommand, AIUsage
from driver.models import Driver
from order.models import Order, OrderOffer, OrderStatus
from users.models import User, UserRole

from Admin_panel.schemas import (
    AdminDashboardStats,
    AdminUserUpdate,
    AdminOrderUpdate,
    OrdersByDay,
)


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
        like = f"%{search.strip()}%"
        base = base.where(
            or_(
                User.full_name.ilike(like),
                User.username.ilike(like),
                User.phone_number.ilike(like),
                User.email.ilike(like),
            )
        )

    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = base.order_by(desc(User.created_at)).offset(max(skip, 0)).limit(min(max(limit, 1), 200))
    rows = (await db.execute(stmt)).scalars().all()
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
    base = select(Order)
    if status:
        base = base.where(Order.status == status)
    if customer_id is not None:
        base = base.where(Order.customer_id == customer_id)
    if driver_id is not None:
        base = base.where(Order.driver_id == driver_id)
    if date_from:
        base = base.where(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        base = base.where(Order.created_at <= datetime.combine(date_to, datetime.max.time()))

    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = (
        base.options(selectinload(Order.waypoints))
        .order_by(desc(Order.created_at))
        .offset(max(skip, 0))
        .limit(min(max(limit, 1), 200))
    )
    rows = (await db.execute(stmt)).scalars().all()
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

    by_status_rows = (
        await db.execute(select(Order.status, func.count(Order.id)).group_by(Order.status))
    ).all()
    orders_by_status = {
        (s.value if hasattr(s, "value") else str(s)): int(c) for s, c in by_status_rows
    }
    for s in OrderStatus:
        orders_by_status.setdefault(s.value, 0)

    offers_today = (
        await db.execute(
            select(func.count(OrderOffer.id)).where(
                OrderOffer.created_at.between(today_start, today_end)
            )
        )
    ).scalar_one()

    ai_today_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(AIUsage.requests), 0),
                func.coalesce(func.sum(AIUsage.input_tokens), 0),
                func.coalesce(func.sum(AIUsage.output_tokens), 0),
            ).where(AIUsage.usage_date == today)
        )
    ).one()
    ai_requests_today = int(ai_today_row[0])
    ai_input_tokens_today = int(ai_today_row[1])
    ai_output_tokens_today = int(ai_today_row[2])

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
        orders_by_status=orders_by_status,
        offers_today=int(offers_today),
        ai_requests_today=ai_requests_today,
        ai_input_tokens_today=ai_input_tokens_today,
        ai_output_tokens_today=ai_output_tokens_today,
        orders_last_7_days=last_7,
    )


# ════════════════════════════════════════════════════════════
# AI COMMANDS LOG
# ════════════════════════════════════════════════════════════


async def list_ai_commands(
    db: AsyncSession,
    *,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    command_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[AICommand], int]:
    base = select(AICommand)
    if user_id is not None:
        base = base.where(AICommand.user_id == user_id)
    if status:
        base = base.where(AICommand.status == status)
    if command_type:
        base = base.where(AICommand.command_type == command_type)

    total_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = (
        base.order_by(desc(AICommand.created_at))
        .offset(max(skip, 0))
        .limit(min(max(limit, 1), 200))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), int(total)
