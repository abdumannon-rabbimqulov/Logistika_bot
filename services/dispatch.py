"""Avtomatik dispatch: buyurtmani ketma-ket haydovchilarga taklif qilish.

Bitta order uchun bir vaqtning o'zida faqat BITTA `pending` `DispatchAttempt` bo'ladi —
eng yaqin/mos haydovchiga yuboriladi, u rad etsa yoki 60s ichida javob bermasa, keyingi
nomzodga o'tiladi (jami `MAX_ROUNDS` marta). Hech kim qabul qilmasa senderga narxni
oshirish taklif qilinadi. Shu tuzilma eski "ochiq ro'yxat + self-assign" yondashuvidagi
poyga sharoitini (race condition) tabiiy ravishda yo'q qiladi: bir vaqtda faqat bitta
haydovchida faol taklif bor, va uni qabul qilish atomik `UPDATE ... WHERE status='pending'`
orqali amalga oshadi.

Ushbu modul FastAPI endpointlaridan (`order/router.py`, WebApp uchun) HAM, aiogram bot
callback handleridan (`handlers/dispatch.py`, Telegram tugmalari uchun) HAM chaqiriladi —
mantiq bir joyda, ikki marta yozilmaydi (docs/DISPATCH_SYSTEM_PLAN.md 8-bo'lim).

Timer: alohida scheduler/Redis job store o'rniga (yangi og'ir bog'liqlik kerak bo'lardi)
har bir urinish uchun `asyncio.create_task` bilan 60s kutish tasklari ishlatiladi, va
`config/main.py`dagi FastAPI lifespan'da davriy "sweep" (muddati o'tgan-u hali pending
qolganlarni tozalaydi) — process qayta ishga tushsa ham tiklanish uchun zaxira.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

import driver.crud as driver_crud
import order.crud as order_crud
from driver.models import Driver
from order.dispatch_models import DispatchAttempt, DispatchAttemptStatus, DispatchMatchType
from order.models import Order, OrderStatus
from services import live_location, notifications
from utils.geo import calculate_distance_km

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5
RESPONSE_TIMEOUT_SEC = 60


class DispatchError(Exception):
    """Dispatch amalini bajarib bo'lmadi (foydalanuvchiga ko'rsatiladigan sabab bilan)."""

    def __init__(self, message: str, *, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def _round_price(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def _pickup_info(order: Order) -> tuple[Optional[float], Optional[float], Optional[str]]:
    origin = order.origin
    if not origin:
        return None, None, None
    lat = float(origin.latitude) if origin.latitude is not None else None
    lon = float(origin.longitude) if origin.longitude is not None else None
    return lat, lon, origin.address


def _region_matches(pickup_address: Optional[str], driver_field: Optional[str]) -> bool:
    if not pickup_address or not driver_field or not driver_field.strip():
        return False
    return driver_field.strip().lower() in pickup_address.lower()


async def _find_next_candidate(
    db: AsyncSession, order: Order, exclude_driver_ids: set[int]
) -> Optional[tuple[Driver, DispatchMatchType, Optional[Decimal]]]:
    pickup_lat, pickup_lon, pickup_address = _pickup_info(order)

    # Tier A — jonli GPS (eng aniq): Redis'dagi online haydovchilar orasidan pickup
    # nuqtasigacha eng yaqinini tanlaydi.
    if pickup_lat is not None and pickup_lon is not None:
        online = await live_location.get_all_online_drivers()
        ranked: list[tuple[int, float]] = []
        for entry in online:
            try:
                driver_id = int(entry["driver_id"])
            except (KeyError, TypeError, ValueError):
                continue
            if driver_id in exclude_driver_ids:
                continue
            if entry.get("truck_type_id") != order.required_truck_type_id:
                continue
            dist = calculate_distance_km(pickup_lat, pickup_lon, entry.get("lat"), entry.get("lon"))
            if dist is None:
                continue
            ranked.append((driver_id, dist))
        ranked.sort(key=lambda pair: pair[1])

        if ranked:
            candidate_ids = [driver_id for driver_id, _ in ranked]
            result = await db.execute(
                select(Driver).where(
                    Driver.id.in_(candidate_ids),
                    Driver.is_available.is_(True),
                    Driver.is_blocked.is_(False),
                    Driver.docs_verified.is_(True),
                    or_(Driver.available_from_date.is_(None), Driver.available_from_date <= order.pickup_at.date()),
                )
            )
            eligible = {d.id: d for d in result.scalars().all()}
            for driver_id, dist in ranked:
                driver = eligible.get(driver_id)
                if driver:
                    return driver, DispatchMatchType.GPS, Decimal(str(round(dist, 2)))

    # Tier B — GPS live emas: region/shahar matn moslik bo'yicha fallback,
    # ishonchlilik balli (reliability_score) bo'yicha saralanadi.
    query = select(Driver).where(
        Driver.truck_type_id == order.required_truck_type_id,
        Driver.is_available.is_(True),
        Driver.is_blocked.is_(False),
        Driver.docs_verified.is_(True),
        or_(Driver.available_from_date.is_(None), Driver.available_from_date <= order.pickup_at.date()),
    )
    if exclude_driver_ids:
        query = query.where(Driver.id.notin_(exclude_driver_ids))
    query = query.order_by(Driver.reliability_score.desc())
    result = await db.execute(query)
    for driver in result.scalars().all():
        if _region_matches(pickup_address, driver.current_city) or _region_matches(pickup_address, driver.current_region):
            return driver, DispatchMatchType.REGION, None

    return None


def _offer_text(order: Order, attempt: DispatchAttempt) -> str:
    origin = order.origin
    destination = order.destination
    origin_addr = origin.address if origin and origin.address else "?"
    dest_addr = destination.address if destination and destination.address else "?"
    distance_note = f"\n📍 Sizgacha: ~{attempt.distance_km} km" if attempt.distance_km is not None else ""
    return (
        f"🚚 Yangi buyurtma taklifi ({attempt.round_number}/{MAX_ROUNDS})\n"
        f"Yuk: {order.cargo_name} ({order.weight}t)\n"
        f"{origin_addr} → {dest_addr}\n"
        f"Masofa: {order.total_distance_km} km\n"
        f"💰 Narx: {order.price} {order.currency}"
        f"{distance_note}\n\n"
        f"⏱ 60 soniya ichida javob bering"
    )


async def _previously_attempted_driver_ids(db: AsyncSession, order_id: int) -> set[int]:
    result = await db.execute(select(DispatchAttempt.driver_id).where(DispatchAttempt.order_id == order_id))
    return set(result.scalars().all())


async def start_dispatch(db: AsyncSession, order: Order) -> None:
    """Order yaratilgandan keyin chaqiriladi — 1-urinishni boshlaydi."""
    await _dispatch_next(db, order)


async def _dispatch_next(db: AsyncSession, order: Order) -> None:
    if order.status != OrderStatus.PENDING or order.driver_id is not None:
        return

    if order.dispatch_round >= MAX_ROUNDS:
        await _request_price_bump(db, order)
        return

    exclude = await _previously_attempted_driver_ids(db, order.id)
    candidate = await _find_next_candidate(db, order, exclude)
    if candidate is None:
        await _request_price_bump(db, order)
        return

    driver, match_type, distance_km = candidate
    now = datetime.now(timezone.utc)
    order.dispatch_round += 1
    attempt = DispatchAttempt(
        order_id=order.id,
        driver_id=driver.id,
        round_number=order.dispatch_round,
        match_type=match_type,
        distance_km=distance_km,
        status=DispatchAttemptStatus.PENDING,
        sent_at=now,
        expires_at=now + timedelta(seconds=RESPONSE_TIMEOUT_SEC),
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)

    chat_id = driver.user_id
    keyboard = notifications.inline_keyboard(
        [[("✅ Qabul qilish", f"dispatch:accept:{attempt.id}"), ("❌ Rad etish", f"dispatch:reject:{attempt.id}")]]
    )
    message_id = await notifications.send_telegram_message(chat_id, _offer_text(order, attempt), reply_markup=keyboard)
    if message_id:
        attempt.bot_chat_id = chat_id
        attempt.bot_message_id = message_id
        await db.commit()

    asyncio.create_task(_expire_after_timeout(attempt.id))


async def _expire_after_timeout(attempt_id: int) -> None:
    from config.config import async_session

    await asyncio.sleep(RESPONSE_TIMEOUT_SEC + 2)
    async with async_session() as db:
        try:
            await expire_attempt(db, attempt_id)
        except Exception:
            logger.exception("Dispatch attempt #%s muddati tugashini qayta ishlashda xato", attempt_id)


async def expire_attempt(db: AsyncSession, attempt_id: int) -> None:
    result = await db.execute(
        update(DispatchAttempt)
        .where(DispatchAttempt.id == attempt_id, DispatchAttempt.status == DispatchAttemptStatus.PENDING)
        .values(status=DispatchAttemptStatus.EXPIRED, responded_at=datetime.now(timezone.utc))
        .returning(DispatchAttempt.order_id, DispatchAttempt.bot_chat_id, DispatchAttempt.bot_message_id)
    )
    row = result.first()
    if row is None:
        await db.rollback()
        return
    await db.commit()

    if row.bot_chat_id and row.bot_message_id:
        await notifications.edit_telegram_message(
            row.bot_chat_id, row.bot_message_id, "⏱ Vaqt tugadi — buyurtma boshqa haydovchiga yuborildi"
        )

    order = await order_crud.get_order(db, row.order_id)
    if order:
        await _dispatch_next(db, order)


async def sweep_expired(db: AsyncSession) -> int:
    """Muddati o'tgan-u hali `pending` qolgan urinishlarni topib yopadi va navbatni davom
    ettiradi. Process qayta ishga tushganda (asyncio tasklari yo'qolganda) tiklanish uchun."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(DispatchAttempt.id).where(
            DispatchAttempt.status == DispatchAttemptStatus.PENDING, DispatchAttempt.expires_at <= now
        )
    )
    attempt_ids = list(result.scalars().all())
    for attempt_id in attempt_ids:
        await expire_attempt(db, attempt_id)
    return len(attempt_ids)


async def accept_attempt(db: AsyncSession, attempt_id: int, *, acting_user_id: int) -> Order:
    driver = await driver_crud.get_driver_by_user_id(db, acting_user_id)
    if not driver:
        raise DispatchError("Haydovchi profili topilmadi", status_code=404)
    if driver.is_blocked:
        raise DispatchError(
            "Siz bloklangansiz — buyurtma qabul qila olmaysiz. Sababi: " + (driver.block_reason or "noma'lum"),
            status_code=403,
        )

    result = await db.execute(
        update(DispatchAttempt)
        .where(
            DispatchAttempt.id == attempt_id,
            DispatchAttempt.status == DispatchAttemptStatus.PENDING,
            DispatchAttempt.driver_id == driver.id,
        )
        .values(status=DispatchAttemptStatus.ACCEPTED, responded_at=datetime.now(timezone.utc))
        .returning(DispatchAttempt.order_id, DispatchAttempt.bot_chat_id, DispatchAttempt.bot_message_id)
    )
    row = result.first()
    if row is None:
        await db.rollback()
        raise DispatchError("Bu taklif sizga tegishli emas yoki allaqachon javob berilgan", status_code=409)
    await db.commit()

    order = await order_crud.get_order(db, row.order_id)
    if order is None or order.driver_id is not None:
        # Juda kam ehtimol: order shu orada (masalan admin qo'lda) boshqa yo'l bilan
        # allaqachon biriktirilgan bo'lib chiqdi — attempt endi noto'g'ri "accepted" holatda
        # qolmasligi uchun orqaga CANCELLED qilinadi (ma'lumot mosligini saqlash uchun).
        await db.execute(
            update(DispatchAttempt).where(DispatchAttempt.id == attempt_id).values(status=DispatchAttemptStatus.CANCELLED)
        )
        await db.commit()
        raise DispatchError("Buyurtma allaqachon boshqa haydovchiga biriktirilgan", status_code=409)

    order.driver_id = driver.id
    order.status = OrderStatus.ACCEPTED
    await db.commit()
    await db.refresh(order, attribute_names=["driver_id", "status", "updated_at"])

    # Ehtiyot chorasi (odatda bo'sh): ketma-ket dispatch bo'lgani uchun shu order uchun
    # boshqa pending attempt bo'lmasligi kerak, lekin himoya qatlami sifatida yopib qo'yiladi.
    await db.execute(
        update(DispatchAttempt)
        .where(DispatchAttempt.order_id == order.id, DispatchAttempt.status == DispatchAttemptStatus.PENDING)
        .values(status=DispatchAttemptStatus.CANCELLED)
    )
    await db.commit()

    if row.bot_chat_id and row.bot_message_id:
        await notifications.edit_telegram_message(row.bot_chat_id, row.bot_message_id, "✅ Siz bu buyurtmani qabul qildingiz!")

    await _notify_sender_driver_found(db, order, driver)
    return order


async def reject_attempt(db: AsyncSession, attempt_id: int, *, acting_user_id: int) -> None:
    driver = await driver_crud.get_driver_by_user_id(db, acting_user_id)
    if not driver:
        raise DispatchError("Haydovchi profili topilmadi", status_code=404)

    result = await db.execute(
        update(DispatchAttempt)
        .where(
            DispatchAttempt.id == attempt_id,
            DispatchAttempt.status == DispatchAttemptStatus.PENDING,
            DispatchAttempt.driver_id == driver.id,
        )
        .values(status=DispatchAttemptStatus.REJECTED, responded_at=datetime.now(timezone.utc))
        .returning(DispatchAttempt.order_id, DispatchAttempt.bot_chat_id, DispatchAttempt.bot_message_id)
    )
    row = result.first()
    if row is None:
        await db.rollback()
        raise DispatchError("Bu taklif sizga tegishli emas yoki allaqachon javob berilgan", status_code=409)
    await db.commit()

    if row.bot_chat_id and row.bot_message_id:
        await notifications.edit_telegram_message(row.bot_chat_id, row.bot_message_id, "❌ Siz rad etdingiz")

    order = await order_crud.get_order(db, row.order_id)
    if order:
        await _dispatch_next(db, order)


async def get_active_attempt(db: AsyncSession, driver_id: int) -> Optional[DispatchAttempt]:
    result = await db.execute(
        select(DispatchAttempt)
        .where(DispatchAttempt.driver_id == driver_id, DispatchAttempt.status == DispatchAttemptStatus.PENDING)
        .order_by(DispatchAttempt.sent_at.desc())
    )
    return result.scalars().first()


async def _request_price_bump(db: AsyncSession, order: Order) -> None:
    if order.price_bump_requested_at is not None:
        return  # allaqachon so'ralgan — qayta-qayta yubormaslik uchun
    order.price_bump_requested_at = datetime.now(timezone.utc)
    await db.commit()

    plus10 = _round_price(order.price * Decimal("1.10"))
    plus20 = _round_price(order.price * Decimal("1.20"))
    text = (
        f"😔 '{order.cargo_name}' buyurtmangiz uchun {order.dispatch_round} ta haydovchidan "
        f"hech biri javob bermadi.\n\nJoriy narx: {order.price} {order.currency}\n"
        f"Narxni oshirib qidiruvni davom ettiramizmi?"
    )
    keyboard = notifications.inline_keyboard(
        [
            [(f"+10% ({plus10} {order.currency})", f"pricebump:{order.id}:{plus10}")],
            [(f"+20% ({plus20} {order.currency})", f"pricebump:{order.id}:{plus20}")],
        ]
    )
    await notifications.send_telegram_message(order.customer_id, text, reply_markup=keyboard)


async def apply_price_bump(db: AsyncSession, order: Order, new_price: Decimal) -> Order:
    if order.driver_id is not None:
        raise DispatchError("Buyurtmaga allaqachon haydovchi biriktirilgan", status_code=409)
    if order.dispatch_round < MAX_ROUNDS:
        raise DispatchError("Bu buyurtma uchun narx oshirish hali taklif qilinmagan", status_code=409)

    if order.original_price is None:
        order.original_price = order.price
    order.price = new_price
    order.dispatch_round = 0
    order.price_bump_requested_at = None
    await db.commit()
    await db.refresh(
        order, attribute_names=["price", "original_price", "dispatch_round", "price_bump_requested_at", "updated_at"]
    )

    await _dispatch_next(db, order)
    return order


async def _notify_sender_driver_found(db: AsyncSession, order: Order, driver: Driver) -> None:
    text = f"✅ '{order.cargo_name}' buyurtmangiz uchun haydovchi topildi! ({driver.truck_number})"
    await notifications.send_telegram_message(order.customer_id, text)
