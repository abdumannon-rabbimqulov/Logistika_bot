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
from decimal import Decimal
from typing import Optional

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import driver.crud as driver_crud
import order.crud as order_crud
from driver.models import Driver
from order.dispatch_models import DispatchAttempt, DispatchAttemptStatus, DispatchMatchType
from order.models import Order, OrderStatus
from services import live_location, navigation, notifications, osrm_client, pricing
from utils.geo import calculate_distance_km

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5
RESPONSE_TIMEOUT_SEC = 60

# Jonli GPS o'chgan bo'lsa, DB'dagi oxirgi koordinata shu muddat ichida yozilgan bo'lsa
# hali ham ishonchli deb qaraladi (haydovchi ilovani yopgan, lekin uzoqqa ketmagan).
LAST_LOCATION_MAX_AGE_SEC = 6 * 60 * 60  # 6 soat

# Joylashuvsiz haydovchiga ogohlantirish yuborish oralig'i (spam bo'lmasligi uchun).
WARN_THROTTLE_SEC = 12 * 60 * 60  # 12 soat

# Yo'lga chiqish vaqtigacha shuncha qolganda buyurtma SCHEDULED emas, ACCEPTED bo'ladi
# (ya'ni "hozir yo'lga chiqing"). Undan uzoq bo'lsa — haydovchi topilgan, lekin hali
# kutadi: `OrderStatus.SCHEDULED` aynan shu holat uchun yozilgan edi, lekin shu paytgacha
# hech qachon qo'yilmasdi.
SCHEDULED_LEAD_SEC = 30 * 60  # 30 daqiqa


class DispatchError(Exception):
    """Dispatch amalini bajarib bo'lmadi (foydalanuvchiga ko'rsatiladigan sabab bilan)."""

    def __init__(self, message: str, *, status_code: int = 409):
        super().__init__(message)
        self.status_code = status_code


def _pickup_info(order: Order) -> tuple[Optional[float], Optional[float], Optional[str]]:
    origin = order.origin
    if not origin:
        return None, None, None
    lat = float(origin.latitude) if origin.latitude is not None else None
    lon = float(origin.longitude) if origin.longitude is not None else None
    return lat, lon, origin.address


async def resolve_departure_plan(
    order: Order, driver: Driver
) -> tuple[OrderStatus, Optional[datetime]]:
    """Haydovchi qabul qilganda: buyurtma darhol ACCEPTED bo'ladimi yoki SCHEDULED bo'lib kutadimi.

    `departure_at` — haydovchi yo'lga chiqishi kerak bo'lgan payt: yuklash vaqtidan
    (`pickup_at`) haydovchining yuk ortish nuqtasigacha yetib borish vaqti ayriladi.
    Ustun modelda boshidan bor edi ("tizim hisoblaydi" izohi bilan), lekin hech qachon
    to'ldirilmasdi.

    OSRM ishlamasa yoki haydovchining koordinatasi bo'lmasa — yo'l vaqti hisobga
    olinmaydi va `departure_at = pickup_at` deb qabul qilinadi (buyurtma baribir
    to'g'ri ishlaydi, faqat eslatma aniqroq bo'lmaydi).
    """
    pickup_at = order.pickup_at
    if pickup_at is None:
        return OrderStatus.ACCEPTED, None
    if pickup_at.tzinfo is None:
        pickup_at = pickup_at.replace(tzinfo=timezone.utc)

    departure_at = pickup_at
    pickup_lat, pickup_lon, _ = _pickup_info(order)
    if (
        pickup_lat is not None
        and pickup_lon is not None
        and driver.last_latitude is not None
        and driver.last_longitude is not None
    ):
        try:
            route = await osrm_client.get_route(
                [(driver.last_latitude, driver.last_longitude), (pickup_lat, pickup_lon)]
            )
            departure_at = pickup_at - timedelta(minutes=route.duration_min)
        except osrm_client.OSRMRouteError as exc:
            logger.info(
                "Order #%s uchun yo'lga chiqish vaqti hisoblanmadi (OSRM): %s", order.id, exc
            )

    now = datetime.now(timezone.utc)
    if (departure_at - now).total_seconds() > SCHEDULED_LEAD_SEC:
        return OrderStatus.SCHEDULED, departure_at
    return OrderStatus.ACCEPTED, departure_at


async def promote_due_scheduled(db: AsyncSession) -> int:
    """Yo'lga chiqish vaqti kelgan SCHEDULED buyurtmalarni ACCEPTED ga o'tkazadi.

    `config/main.py` dagi davriy sweep chaqiradi. Har bir buyurtma uchun haydovchiga
    bir marta eslatma yuboriladi.
    """
    now = datetime.now(timezone.utc)
    due_before = now + timedelta(seconds=SCHEDULED_LEAD_SEC)

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(
            Order.status == OrderStatus.SCHEDULED,
            Order.departure_at.is_not(None),
            Order.departure_at <= due_before,
        )
    )
    orders = list(result.scalars().all())
    if not orders:
        return 0

    for order in orders:
        order.status = OrderStatus.ACCEPTED
    await db.commit()

    for order in orders:
        if order.driver_id is None:
            continue
        drv = await driver_crud.get_driver(db, order.driver_id)
        if drv is None:
            continue
        _, _, pickup_address = _pickup_info(order)
        # Driver.user_id — Telegram chat id (dispatch.py'dagi boshqa xabarlar ham shunday yuboriladi).
        await notifications.send_telegram_message(
            drv.user_id,
            f"⏰ '{order.cargo_name}' buyurtmasi uchun yo'lga chiqish vaqti keldi.\n"
            f"Yuk ortish nuqtasi: {pickup_address or 'manzil ko‘rsatilmagan'}",
        )

    return len(orders)


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

    # Barcha "yaroqli" haydovchilar (turi, mavjudligi, hujjatlari bo'yicha) — quyidagi
    # ikki bosqich uchun bir marta o'qiladi.
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
    eligible_drivers = list((await db.execute(query)).scalars().all())

    # Tier A2 — jonli GPS o'chiq, lekin DB'dagi OXIRGI ma'lum koordinata yangi bo'lsa,
    # shu bo'yicha eng yaqini tanlanadi (haydovchi ilovani yopgan, ammo yaqinda
    # translyatsiya qilgan holat). driver/router.py WS handleri bu ustunlarni yozadi.
    if pickup_lat is not None and pickup_lon is not None:
        fresh_after = datetime.now(timezone.utc) - timedelta(seconds=LAST_LOCATION_MAX_AGE_SEC)
        by_last_location: list[tuple[Driver, float]] = []
        for driver in eligible_drivers:
            if driver.last_latitude is None or driver.last_longitude is None:
                continue
            if driver.last_location_at is None or driver.last_location_at < fresh_after:
                continue
            dist = calculate_distance_km(pickup_lat, pickup_lon, driver.last_latitude, driver.last_longitude)
            if dist is not None:
                by_last_location.append((driver, dist))

        if by_last_location:
            by_last_location.sort(key=lambda pair: pair[1])
            driver, dist = by_last_location[0]
            # Match turi GPS: moslashtirish koordinata bo'yicha bo'ldi (jonli emas, oxirgi
            # ma'lum nuqta) — enum'ga yangi qiymat qo'shish migratsiya talab qilardi.
            return driver, DispatchMatchType.GPS, Decimal(str(round(dist, 2)))

    # Tier B — koordinata umuman yo'q: region/shahar matn moslik bo'yicha fallback,
    # ishonchlilik balli (reliability_score) bo'yicha saralangan holda.
    for driver in eligible_drivers:
        if _region_matches(pickup_address, driver.current_city) or _region_matches(pickup_address, driver.current_region):
            return driver, DispatchMatchType.REGION, None

    return None


async def _warn_unlocatable_drivers(db: AsyncSession, order: Order) -> None:
    """Joylashuvi umuman aniqlanmaydigan haydovchilarni Telegram orqali ogohlantiradi.

    Bunday haydovchi hech qachon taklif ololmaydi: jonli GPS o'chiq, oxirgi ma'lum
    koordinatasi yo'q (yoki eskirgan) va viloyat/shahar ham ko'rsatilmagan. Buyurtmaga
    nomzod topilmaganda chaqiriladi — ya'ni ular tufayli yuk qidiruvsiz qolgan paytda.

    Bir haydovchiga `WARN_THROTTLE_SEC` ichida faqat bitta xabar yuboriladi.
    """
    result = await db.execute(
        select(Driver).where(
            Driver.truck_type_id == order.required_truck_type_id,
            Driver.is_available.is_(True),
            Driver.is_blocked.is_(False),
            Driver.docs_verified.is_(True),
        )
    )
    drivers = list(result.scalars().all())
    if not drivers:
        return

    online_ids = set()
    try:
        online_ids = {int(e["driver_id"]) for e in await live_location.get_all_online_drivers() if e.get("driver_id")}
    except Exception:
        logger.exception("Online haydovchilar ro'yxatini olishda xato (ogohlantirish uchun)")

    fresh_after = datetime.now(timezone.utc) - timedelta(seconds=LAST_LOCATION_MAX_AGE_SEC)

    for driver in drivers:
        if driver.id in online_ids:
            continue  # jonli GPS bor — ogohlantirish kerak emas
        has_recent_point = (
            driver.last_latitude is not None
            and driver.last_longitude is not None
            and driver.last_location_at is not None
            and driver.last_location_at >= fresh_after
        )
        has_region = bool((driver.current_region or "").strip() or (driver.current_city or "").strip())
        if has_recent_point or has_region:
            continue

        if not await live_location.claim_notice_slot(f"dispatch_geo_warn:{driver.id}", WARN_THROTTLE_SEC):
            continue

        await notifications.send_telegram_message(
            driver.user_id,
            "📍 Sizga mos yuk chiqdi, lekin joylashuvingiz aniqlanmadi — shuning uchun "
            "taklif yuborilmadi.\n\n"
            "Ilovada GPS'ni yoqing (bosh sahifadagi xarita) yoki \"Liniyaga chiqish\" "
            "oynasida viloyatingizni ko'rsating — shundan keyin yuklar sizga ham taklif qilinadi.",
        )
        logger.info("Driver #%s joylashuvsiz — Telegram orqali ogohlantirildi", driver.id)


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


async def _send_navigation_links(order: Order, chat_id: int) -> None:
    """Buyurtma qabul qilingandan keyin haydovchiga navigatsiya havolalarini yuboradi.

    Marshrut bizning ilovada chizilmaydi — haydovchi tugmani bosib o'zi odatlangan
    ilovasida (Yandex/Google) ochadi. Koordinata yo'q bo'lsa tugma ko'rsatilmaydi.
    """
    origin, destination = order.origin, order.destination
    keyboard = notifications.url_keyboard(
        [
            [
                ("🧭 Yuk olish joyiga (Yandex)", navigation.yandex_point_url(origin)),
                ("🧭 Google", navigation.google_point_url(origin)),
            ],
            [
                ("🗺 To'liq marshrut (Yandex)", navigation.yandex_route_url(origin, destination)),
                ("🗺 Google", navigation.google_route_url(origin, destination)),
            ],
        ]
    )
    if keyboard is None:
        return

    origin_addr = origin.address if origin and origin.address else "?"
    dest_addr = destination.address if destination and destination.address else "?"
    await notifications.send_telegram_message(
        chat_id,
        f"📍 Yuk olish: {origin_addr}\n🏁 Yetkazish: {dest_addr}\n\n"
        "Marshrutni quyidagi tugmalar orqali o'zingizga qulay ilovada oching:",
        reply_markup=keyboard,
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
        # Nomzod topilmadi — joylashuvi umuman aniqlanmagan (GPS ham, viloyat ham yo'q)
        # haydovchilarga sabab tushuntiriladi, aks holda ular "nega yuk kelmayapti"
        # degan savolda qolardi. Xato bo'lsa ham asosiy oqim to'xtamaydi.
        try:
            await _warn_unlocatable_drivers(db, order)
        except Exception:
            logger.exception("Joylashuvsiz haydovchilarni ogohlantirishda xato (order #%s)", order.id)
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
    # order.dispatch_round UPDATE qilindi -> `updated_at` (server onupdate) expired bo'ladi.
    # Chaqiruvchi (masalan POST /orders) javobni sinxron serializatsiya qilgani uchun
    # o'sha yerda lazy refresh MissingGreenlet beradi — shuning uchun shu yerda tiklanadi.
    await db.refresh(order, attribute_names=["dispatch_round", "updated_at"])

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

    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(DispatchAttempt)
        .where(
            DispatchAttempt.id == attempt_id,
            DispatchAttempt.status == DispatchAttemptStatus.PENDING,
            DispatchAttempt.driver_id == driver.id,
            # Muddati o'tgan taklifni qabul qilib bo'lmaydi — sweep/timer task hali
            # ishlamagan bo'lsa ham (0 qator yangilanadi va quyida 409 qaytadi).
            DispatchAttempt.expires_at > now,
        )
        .values(status=DispatchAttemptStatus.ACCEPTED, responded_at=now)
        .returning(DispatchAttempt.order_id, DispatchAttempt.bot_chat_id, DispatchAttempt.bot_message_id)
    )
    row = result.first()
    if row is None:
        await db.rollback()
        raise DispatchError(
            "Bu taklif sizga tegishli emas, muddati tugagan yoki allaqachon javob berilgan",
            status_code=409,
        )
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
    # Yuklash vaqti hali uzoq bo'lsa buyurtma darhol ACCEPTED emas, SCHEDULED bo'ladi
    # va yo'lga chiqish vaqti (`departure_at`) hisoblanadi — vaqt yaqinlashganda
    # `promote_due_scheduled` uni ACCEPTED ga o'tkazib, haydovchiga eslatma yuboradi.
    order.status, order.departure_at = await resolve_departure_plan(order, driver)
    await db.commit()
    await db.refresh(order, attribute_names=["driver_id", "status", "departure_at", "updated_at"])

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

    await _send_navigation_links(order, driver.user_id)
    await _notify_sender_driver_found(db, order, driver)
    return order


async def assign_driver_manually(db: AsyncSession, order: Order, driver: Driver) -> Order:
    """Admin qo'lda haydovchi biriktiradi (dispatch navbatidan tashqari).

    `accept_attempt` bilan bir xil yon ta'sirlar: order ACCEPTED bo'ladi, shu order
    uchun ochiq qolgan takliflar bekor qilinadi, haydovchiga navigatsiya havolalari
    va senderga "haydovchi topildi" xabari yuboriladi. Shu sababli mantiq bu yerda —
    router'da takrorlanmaydi.
    """
    if driver.is_blocked:
        raise DispatchError(
            "Haydovchi bloklangan — biriktirib bo'lmaydi. Sababi: " + (driver.block_reason or "noma'lum"),
            status_code=409,
        )
    if order.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
        raise DispatchError("Yakunlangan yoki bekor qilingan buyurtmaga haydovchi biriktirilmaydi", status_code=409)

    # Atomik: `WHERE driver_id IS NULL` — bir vaqtda kelgan ikkinchi so'rov None oladi.
    updated = await order_crud.assign_driver(db, order, driver.id)
    if updated is None:
        raise DispatchError("Buyurtmaga allaqachon haydovchi biriktirilgan", status_code=409)

    # Ochiq qolgan takliflar yopiladi — aks holda boshqa haydovchi ham "qabul qildim"
    # deb bosishi va 409 olishi mumkin edi (foydalanuvchi uchun chalkash).
    await db.execute(
        update(DispatchAttempt)
        .where(DispatchAttempt.order_id == order.id, DispatchAttempt.status == DispatchAttemptStatus.PENDING)
        .values(status=DispatchAttemptStatus.CANCELLED)
    )
    await db.commit()

    await notifications.send_telegram_message(
        driver.user_id,
        f"📦 Sizga admin tomonidan '{order.cargo_name}' buyurtmasi biriktirildi.",
    )
    await _send_navigation_links(order, driver.user_id)
    await _notify_sender_driver_found(db, order, driver)
    return updated


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
    """Haydovchining hozir javob kutayotgan taklifi (muddati o'tmagan).

    `order` va `order.waypoints` oldindan (eager) yuklanadi: chaqiruvchi (order/router.py
    `GET /orders/dispatch/active`) taklif kartasi uchun yo'nalish/narx xulosasini shu
    obyektlardan o'qiydi — async kontekstda lazy-load `MissingGreenlet` bilan yiqiladi.

    `expires_at > now` sharti muhim: muddati o'tgan-u hali sweep qilinmagan attempt
    qaytsa, WebApp kartasi 0 soniya bilan qayta-qayta miltillaydi.
    """
    result = await db.execute(
        select(DispatchAttempt)
        .options(selectinload(DispatchAttempt.order).selectinload(Order.waypoints))
        .where(
            DispatchAttempt.driver_id == driver_id,
            DispatchAttempt.status == DispatchAttemptStatus.PENDING,
            DispatchAttempt.expires_at > datetime.now(timezone.utc),
        )
        .order_by(DispatchAttempt.sent_at.desc())
    )
    return result.scalars().first()


async def _request_price_bump(db: AsyncSession, order: Order) -> None:
    if order.price_bump_requested_at is not None:
        return  # allaqachon so'ralgan — qayta-qayta yubormaslik uchun
    order.price_bump_requested_at = datetime.now(timezone.utc)
    await db.commit()
    # _dispatch_next dagi kabi: UPDATE'dan keyin `updated_at` expired qoladi.
    await db.refresh(order, attribute_names=["price_bump_requested_at", "updated_at"])

    text = (
        f"😔 '{order.cargo_name}' buyurtmangiz uchun {order.dispatch_round} ta haydovchidan "
        f"hech biri javob bermadi.\n\nJoriy narx: {order.price} {order.currency}\n"
        f"Narxni oshirib qidiruvni davom ettiramizmi?"
    )
    # 5 ta belgilangan variant (+100 000 ... +500 000 UZS) — WebApp'dagi narx tahrirlash
    # ekrani bilan aynan bir xil ro'yxat (services/pricing.py).
    keyboard = notifications.inline_keyboard(
        [
            [(
                f"+{option['increment']:,.0f} ({option['price']:,.0f} {order.currency})".replace(",", " "),
                f"pricebump:{order.id}:{option['price']}",
            )]
            for option in pricing.quick_price_options(order.price)
        ]
    )
    await notifications.send_telegram_message(order.customer_id, text, reply_markup=keyboard)


async def apply_price_bump(db: AsyncSession, order: Order, new_price: Decimal) -> Order:
    if order.driver_id is not None:
        raise DispatchError("Buyurtmaga allaqachon haydovchi biriktirilgan", status_code=409)
    if order.dispatch_round < MAX_ROUNDS:
        raise DispatchError("Bu buyurtma uchun narx oshirish hali taklif qilinmagan", status_code=409)

    # Bu endpoint narxni oshirish uchun, lekin qiymat mijozdan keladi — qo'lda tahrirlash
    # bilan bir xil chegara (SENDER_MAX_DISCOUNT_PERCENT) shu yerda ham tekshiriladi.
    base_price = order_crud.order_base_price(order)
    try:
        new_price = await pricing.validate_custom_price_for_db(db, new_price, base_price)
    except pricing.PriceValidationError as exc:
        raise DispatchError(str(exc), status_code=400) from exc

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
