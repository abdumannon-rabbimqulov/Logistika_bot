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

Bajarilish joyi: chaqiruvchi (API/bot) faqat vazifani RabbitMQ navbatiga qo'yadi
(`_dispatch_next` → `services/queue.py`), haqiqiy qidiruv esa alohida jarayonda —
`workers/dispatch_worker.py` `run_dispatch_job()` ni chaqiradi. Shu sababli sender
narxni oshirganda HTTP javob darhol qaytadi, va bir vaqtda qidirilayotgan buyurtmalar
soni worker'ning `DISPATCH_PREFETCH` cheklovi bilan chegaralanadi (hammasi birdaniga
qidirilib DB/Telegram/OSRM ni bo'g'ib qo'ymaydi).

Timer: haydovchiga berilgan 60 soniya `dispatch.delayed` navbati (TTL + dead-letter)
orqali kutiladi — jarayon qayta ishga tushsa yo'qoladigan `asyncio` taymerlari o'rniga.
Zaxira sifatida worker'da davriy "sweep" ishlaydi (muddati o'tgan-u hali pending
qolgan urinishlarni yopadi) — broker xabari yo'qolgan holat uchun.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import driver.crud as driver_crud
import order.crud as order_crud
from config.config import APP_TIMEZONE, DISPATCH_LEAD_HOURS
from driver.models import Driver
from order.dispatch_models import DispatchAttempt, DispatchAttemptStatus, DispatchMatchType
from order.models import Order, OrderStatus
from services import live_location, navigation, notifications, osrm_client, pricing, queue
from utils.geo import calculate_distance_km

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5
RESPONSE_TIMEOUT_SEC = 60

# Rejalashtirilgan buyurtma uchun qidiruv yuklashdan shuncha oldin boshlanadi.
# DIQQAT: bu quyidagi `SCHEDULED_LEAD_SEC` EMAS — u haydovchi allaqachon topilgandan
# keyin SCHEDULED→ACCEPTED o'tishi uchun (30 daqiqa). Bu esa qidiruvning O'ZI qachon
# boshlanishini belgilaydi.
DISPATCH_START_LEAD_SEC = DISPATCH_LEAD_HOURS * 3600

# Sender narxni ko'pi bilan shuncha marta oshira oladi. Cheklovsiz bo'lsa haydovchisi
# yo'q yo'nalishda "oshir → topilmadi → yana oshir" sikli cheksiz aylanardi.
MAX_PRICE_BUMPS = 3

# Bir order uchun bir vaqtda ikkita qidiruv vazifasi ishlamasligi uchun qulf muddati
# (takroriy yetkazishda ortiqcha ish qilmaslik uchun; to'g'rilikni DB holati saqlaydi).
DISPATCH_LOCK_TTL_SEC = 30

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


_LOCAL_TZ = ZoneInfo(APP_TIMEZONE)


def local_pickup_date(order: Order) -> date:
    """Yuklash sanasi FOYDALANUVCHI mintaqasida (UTC'da emas).

    Haydovchi "2-avgustdan yuk olaman" deganda mahalliy kalendar sanani nazarda tutadi.
    `pickup_at` esa UTC saqlanadi: 2-avgust 03:00 (Toshkent, UTC+5) UTC'da 1-avgust
    22:00 bo'ladi va `.date()` `08-01` qaytaradi. Shunda 2-avgustdan liniyaga chiqqan
    haydovchi aynan 2-avgustdagi yukni olmay qolardi. Taqqoslash bir mintaqada
    bajarilishi shart.
    """
    pickup_at = order.pickup_at
    if pickup_at.tzinfo is None:
        pickup_at = pickup_at.replace(tzinfo=timezone.utc)
    return pickup_at.astimezone(_LOCAL_TZ).date()


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
                    # Sana MAHALLIY mintaqada taqqoslanadi (UTC'da emas) — izoh:
                    # `local_pickup_date`.
                    or_(
                        Driver.available_from_date.is_(None),
                        Driver.available_from_date <= local_pickup_date(order),
                    ),
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
        # Sana MAHALLIY mintaqada (izoh: `local_pickup_date`).
        or_(
            Driver.available_from_date.is_(None),
            Driver.available_from_date <= local_pickup_date(order),
        ),
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
    """Shu buyurtma bo'yicha allaqachon taklif olgan haydovchilar (qayta yubormaslik uchun).

    CANCELLED urinishlar hisobga OLINMAYDI: narx oshirilganda oldingi raundlar aynan shu
    status bilan yopiladi (`apply_price_bump`), ya'ni avval rad etgan haydovchi yangi
    narx bilan qayta taklif oladi — narx oshirishning butun ma'nosi shunda.
    """
    result = await db.execute(
        select(DispatchAttempt.driver_id).where(
            DispatchAttempt.order_id == order_id,
            DispatchAttempt.status != DispatchAttemptStatus.CANCELLED,
        )
    )
    return set(result.scalars().all())


def dispatch_starts_at(order: Order) -> datetime:
    """Shu buyurtma uchun qidiruv boshlanishi kerak bo'lgan payt.

    Yuklash vaqtidan `DISPATCH_START_LEAD_SEC` ayriladi. Yuklash yaqin bo'lsa
    (yoki allaqachon o'tgan bo'lsa) natija o'tmishda bo'ladi — ya'ni "hoziroq".
    """
    pickup_at = order.pickup_at
    if pickup_at.tzinfo is None:
        pickup_at = pickup_at.replace(tzinfo=timezone.utc)
    return pickup_at - timedelta(seconds=DISPATCH_START_LEAD_SEC)


def is_dispatch_due(order: Order, *, now: Optional[datetime] = None) -> bool:
    """Qidiruvni boshlash vaqti keldimi."""
    return dispatch_starts_at(order) <= (now or datetime.now(timezone.utc))


async def start_dispatch(db: AsyncSession, order: Order) -> None:
    """Order yaratilgandan keyin chaqiriladi.

    Yuklash vaqti hali uzoq bo'lsa qidiruv BOSHLANMAYDI — buyurtma `PENDING` va
    `last_dispatch_enqueued_at = NULL` holatida kutadi, worker'dagi davriy
    `enqueue_due_orders` uni vaqti kelganda o'zi navbatga qo'yadi.

    Sabab: ilgari 2 kundan keyingi yuk uchun ham haydovchilarga darhol taklif
    ketardi va qabul qilgan haydovchi shuncha vaqtga band bo'lib qolardi.
    """
    if not is_dispatch_due(order):
        logger.info(
            "Order #%s uchun qidiruv %s da boshlanadi (yuklash: %s)",
            order.id,
            dispatch_starts_at(order).isoformat(),
            order.pickup_at.isoformat(),
        )
        return

    await _dispatch_next(db, order, reason="created")


async def _dispatch_next(db: AsyncSession, order: Order, *, reason: str) -> None:
    """Keyingi qidiruv urinishini RabbitMQ navbatiga qo'yadi (o'zi qidirmaydi).

    Broker ishlamayotgan bo'lsa xato YUTILADI: buyurtma yaratish yoki narx oshirish
    navbat tufayli yiqilmasligi kerak. Bunday buyurtma PENDING holatda qoladi va
    worker'dagi davriy sweep uni keyinroq baribir qidiruvga qaytaradi.
    """
    if order.status != OrderStatus.PENDING or order.driver_id is not None:
        return

    order.last_dispatch_enqueued_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(order, attribute_names=["last_dispatch_enqueued_at", "updated_at"])

    try:
        await queue.publish_dispatch_job(order.id, reason)
    except queue.QueueUnavailable:
        logger.exception(
            "Order #%s uchun qidiruv vazifasi navbatga qo'yilmadi (sabab: %s)", order.id, reason
        )


async def run_dispatch_job(db: AsyncSession, order_id: int, reason: str = "job") -> None:
    """Bitta qidiruv urinishini bajaradi — FAQAT worker chaqiradi.

    Takroriy yetkazishga chidamli: qulf olinmasa yoki buyurtma endi PENDING bo'lmasa
    (haydovchi topilgan / bekor qilingan) hech narsa qilinmaydi.
    """
    lock_key = f"dispatch_job:{order_id}"
    if not await live_location.acquire_lock(lock_key, DISPATCH_LOCK_TTL_SEC):
        logger.info("Order #%s uchun qidiruv allaqachon ishlamoqda — o'tkazib yuborildi", order_id)
        return

    try:
        # Kechiktirilgan ("expired") xabar aynan javob muddati tugagach keladi — avval
        # o'sha urinish yopiladi. `continue_dispatch=False`: keyingi raundni shu yerda
        # o'zimiz davom ettiramiz, aks holda yana bitta xabar navbatga tushib ketardi.
        for attempt_id in await _overdue_attempt_ids(db, order_id):
            await expire_attempt(db, attempt_id, continue_dispatch=False)

        # Haydovchi hali javob berish muddati ichida bo'lsa — aralashmaymiz. Aks holda
        # bitta order uchun ikkita ochiq taklif paydo bo'lardi.
        if await _has_live_attempt(db, order_id):
            return

        order = await order_crud.get_order(db, order_id)
        if order is None:
            logger.warning("Qidiruv vazifasi: order #%s topilmadi", order_id)
            return
        await _run_dispatch_round(db, order)
    finally:
        await live_location.release_lock(lock_key)


async def _run_dispatch_round(db: AsyncSession, order: Order) -> None:
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

    # Javob muddati tugashini kutish: `dispatch.delayed` navbatiga xabar qo'yiladi va
    # TTL tugagach ishlov navbatiga qaytadi. O'shanda `run_dispatch_job` avval muddati
    # o'tgan taklifni yopadi, so'ng keyingi nomzodga o'tadi. Kutilayotgani ATAYLAB
    # attempt emas, order — vazifa mazmuni doim bir xil: "shu buyurtmani qayta ko'r".
    try:
        await queue.publish_dispatch_job(order.id, "expired", delay=True)
    except queue.QueueUnavailable:
        logger.exception(
            "Order #%s uchun kechiktirilgan tekshiruv navbatga qo'yilmadi", order.id
        )


async def _overdue_attempt_ids(db: AsyncSession, order_id: int) -> list[int]:
    """Shu order uchun muddati o'tgan-u hali `pending` qolgan urinishlar."""
    result = await db.execute(
        select(DispatchAttempt.id).where(
            DispatchAttempt.order_id == order_id,
            DispatchAttempt.status == DispatchAttemptStatus.PENDING,
            DispatchAttempt.expires_at <= datetime.now(timezone.utc),
        )
    )
    return list(result.scalars().all())


async def _has_live_attempt(db: AsyncSession, order_id: int) -> bool:
    """Shu order bo'yicha haydovchi hali javob kutayotgan taklif bormi."""
    result = await db.execute(
        select(DispatchAttempt.id)
        .where(
            DispatchAttempt.order_id == order_id,
            DispatchAttempt.status == DispatchAttemptStatus.PENDING,
            DispatchAttempt.expires_at > datetime.now(timezone.utc),
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def expire_attempt(db: AsyncSession, attempt_id: int, *, continue_dispatch: bool = True) -> None:
    """Urinishni EXPIRED qiladi va (standart holatda) keyingi raundni navbatga qo'yadi.

    `continue_dispatch=False` — chaqiruvchi keyingi raundni o'zi bajaradigan holat
    (`run_dispatch_job`): xabar ikki marta navbatga tushmasligi uchun.
    """
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

    if not continue_dispatch:
        return

    order = await order_crud.get_order(db, row.order_id)
    if order:
        await _dispatch_next(db, order, reason="expired")


async def sweep_expired(db: AsyncSession) -> int:
    """Muddati o'tgan-u hali `pending` qolgan urinishlarni topib yopadi va navbatni davom
    ettiradi (worker'da davriy ishlaydi).

    Zaxira mexanizmi: odatda buni `dispatch.delayed` navbatidan qaytgan xabar bajaradi,
    lekin broker o'chgan paytda qo'yilmay qolgan vazifalar shu yerda tiklanadi."""
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


# Buyurtma qidiruvsiz qolgan deb hisoblanadigan muddat (oxirgi navbatga qo'yishdan beri).
STUCK_ORDER_AFTER_SEC = 3 * RESPONSE_TIMEOUT_SEC


def _live_attempt_order_ids():
    """Hozir javob kutilayotgan takliflar bog'langan buyurtma ID lari (subquery)."""
    return (
        select(DispatchAttempt.order_id)
        .where(
            DispatchAttempt.status == DispatchAttemptStatus.PENDING,
            DispatchAttempt.expires_at > datetime.now(timezone.utc),
        )
        .scalar_subquery()
    )


async def enqueue_due_orders(db: AsyncSession) -> int:
    """Qidiruv vaqti kelgan rejalashtirilgan buyurtmalarni navbatga qo'yadi.

    `start_dispatch` yuklash vaqti uzoq bo'lsa buyurtmani ataylab boshlamaydi. Bu
    funksiya (worker'dagi davriy sweep chaqiradi) yuklashgacha
    `DISPATCH_START_LEAD_SEC` qolganda qidiruvni ishga tushiradi.

    Faqat HALI BOSHLANMAGAN buyurtmalar olinadi (`last_dispatch_enqueued_at IS NULL`
    va `dispatch_round == 0`) — allaqachon qidirilayotganini qayta qo'zg'atish
    `requeue_stuck_orders` ning ishi.
    """
    now = datetime.now(timezone.utc)
    due_before = now + timedelta(seconds=DISPATCH_START_LEAD_SEC)

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(
            Order.status == OrderStatus.PENDING,
            Order.driver_id.is_(None),
            Order.dispatch_round == 0,
            Order.last_dispatch_enqueued_at.is_(None),
            Order.price_bump_requested_at.is_(None),
            Order.pickup_at <= due_before,
            Order.id.notin_(_live_attempt_order_ids()),
        )
    )
    orders = list(result.scalars().all())
    for order in orders:
        await _dispatch_next(db, order, reason="scheduled_start")
    if orders:
        logger.info("%s ta rejalashtirilgan buyurtma uchun qidiruv boshlandi", len(orders))
    return len(orders)


async def requeue_stuck_orders(db: AsyncSession) -> int:
    """Navbatga tushmay qolgan PENDING buyurtmalarni qayta qo'yadi.

    Broker publish paytida o'chiq bo'lsa `_dispatch_next` xatoni yutadi va buyurtma
    hech kimga taklif qilinmay qolib ketardi. Bu funksiya aynan shunday buyurtmalarni
    topadi: ochiq taklifi yo'q, narx oshirish ham so'ralmagan, lekin oxirgi urinishdan
    beri `STUCK_ORDER_AFTER_SEC` o'tgan.
    """
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(seconds=STUCK_ORDER_AFTER_SEC)
    due_before = now + timedelta(seconds=DISPATCH_START_LEAD_SEC)

    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(
            Order.status == OrderStatus.PENDING,
            Order.driver_id.is_(None),
            Order.price_bump_requested_at.is_(None),
            Order.dispatch_round < MAX_ROUNDS,
            or_(
                Order.last_dispatch_enqueued_at.is_(None),
                Order.last_dispatch_enqueued_at <= threshold,
            ),
            # Kelajakdagi buyurtma "qidiruvsiz qolgan" EMAS — u ataylab kutmoqda.
            # Bu shartsiz sweep uni darhol qidiruvga tashlab, butun kechiktirishni
            # bekor qilib qo'yardi.
            Order.pickup_at <= due_before,
            Order.id.notin_(_live_attempt_order_ids()),
        )
    )
    orders = list(result.scalars().all())
    for order in orders:
        await _dispatch_next(db, order, reason="requeue")
    if orders:
        logger.warning("%s ta qidiruvsiz qolgan buyurtma navbatga qaytarildi", len(orders))
    return len(orders)


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
        await _dispatch_next(db, order, reason="rejected")


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


async def get_pending_offer_message(db: AsyncSession, order: Order) -> Optional[tuple[int, int]]:
    """Shu buyurtma bo'yicha haydovchiga yuborilgan ochiq taklif xabarining manzili.

    Buyurtma bekor qilinishidan OLDIN chaqirilishi shart: `order/crud.py cancel_order`
    ochiq urinishlarni CANCELLED qilib yopadi va keyin bu so'rov hech narsa topmaydi.

    `notify_offer_cancelled` bilan juftlikda ishlatiladi — WebApp (`order/router.py`)
    va bot (`handlers/dispatch.py`) bekor qilish oqimlari bir xil bo'lishi uchun.
    """
    if order.driver_id is not None or order.status != OrderStatus.PENDING:
        return None

    result = await db.execute(
        select(DispatchAttempt)
        .where(
            DispatchAttempt.order_id == order.id,
            DispatchAttempt.status == DispatchAttemptStatus.PENDING,
        )
        .order_by(DispatchAttempt.sent_at.desc())
    )
    attempt = result.scalars().first()
    if attempt is None or attempt.bot_chat_id is None or attempt.bot_message_id is None:
        return None
    return attempt.bot_chat_id, attempt.bot_message_id


async def notify_offer_cancelled(offer_ref: Optional[tuple[int, int]]) -> None:
    """Taklif olgan haydovchining bot xabarini "bekor qilindi" ga tahrirlaydi.

    Buyurtma haqiqatan bekor qilingandan KEYIN chaqiriladi: aks holda DB xatosida
    haydovchi "bekor qilindi" xabarini olib, buyurtma esa faol qolib ketardi.
    """
    if offer_ref is None:
        return
    chat_id, message_id = offer_ref
    await notifications.edit_telegram_message(chat_id, message_id, "Bu buyurtma bekor qilindi")


def price_bump_keyboard(order: Order):
    """"Haydovchi topilmadi" xabarining tugmalari: narxni oshirish yoki bekor qilish.

    Alohida funksiya, chunki bot handleri (`handlers/dispatch.py`) bekor qilishdan
    voz kechilganda shu klaviaturani qayta tiklaydi.

    5 ta belgilangan variant (+100 000 ... +500 000 UZS) — WebApp'dagi narx tahrirlash
    ekrani bilan aynan bir xil ro'yxat (`services/pricing.py`). Oxirgi qator — voz
    kechish yo'li: narx oshirish yagona chiqish bo'lib qolmasligi kerak.
    """
    return notifications.inline_keyboard(
        [
            [(
                f"+{option['increment']:,.0f} ({option['price']:,.0f} {order.currency})".replace(",", " "),
                f"pricebump:{order.id}:{option['price']}",
            )]
            for option in pricing.quick_price_options(order.price)
        ]
        + [[("❌ Buyurtmani bekor qilish", f"ordercancel:{order.id}")]]
    )


async def _request_price_bump(db: AsyncSession, order: Order) -> None:
    if order.price_bump_requested_at is not None:
        return  # allaqachon so'ralgan — qayta-qayta yubormaslik uchun
    order.price_bump_requested_at = datetime.now(timezone.utc)
    await db.commit()
    # _dispatch_next dagi kabi: UPDATE'dan keyin `updated_at` expired qoladi.
    await db.refresh(order, attribute_names=["price_bump_requested_at", "updated_at"])

    # Nomzod umuman topilmagan bo'lsa raund soni 0 bo'lishi mumkin — "0 ta haydovchi
    # javob bermadi" degan g'alati matn chiqmasligi uchun ikki xil jumla.
    if order.dispatch_round > 0:
        reason_text = (
            f"'{order.cargo_name}' buyurtmangiz uchun {order.dispatch_round} ta "
            "haydovchidan hech biri javob bermadi."
        )
    else:
        reason_text = f"'{order.cargo_name}' buyurtmangiz uchun mos haydovchi topilmadi."

    text = (
        f"😔 {reason_text}\n\nJoriy narx: {order.price} {order.currency}\n"
        f"Narxni oshirib qidiruvni davom ettiramizmi?"
    )
    await notifications.send_telegram_message(
        order.customer_id, text, reply_markup=price_bump_keyboard(order)
    )


async def apply_price_bump(db: AsyncSession, order: Order, new_price: Decimal) -> Order:
    """Sender narxni oshiradi — buyurtma qayta qidiruvga (PENDING) qaytadi.

    Qidiruvning o'zi shu yerda BAJARILMAYDI: navbatga qo'yiladi va worker ko'taradi,
    shuning uchun WebApp/bot tugmasi darhol javob oladi.
    """
    if order.driver_id is not None:
        raise DispatchError("Buyurtmaga allaqachon haydovchi biriktirilgan", status_code=409)
    if order.status in (OrderStatus.COMPLETED, OrderStatus.CANCELLED):
        raise DispatchError(
            "Yakunlangan yoki bekor qilingan buyurtma narxini oshirib bo'lmaydi", status_code=409
        )
    # DIQQAT: shart `dispatch_round >= MAX_ROUNDS` EMAS. Haydovchi umuman topilmaganda
    # (`_run_dispatch_round` da nomzod yo'q) narx oshirish 1-raunddayoq taklif qilinadi —
    # eski shart o'sha holatda tugmani 409 bilan rad etardi, ya'ni taklif ko'rinardi-yu
    # ishlamasdi. Yagona to'g'ri mezon — taklif haqiqatan yuborilganmi.
    if order.price_bump_requested_at is None:
        raise DispatchError("Bu buyurtma uchun narx oshirish hali taklif qilinmagan", status_code=409)
    if order.price_bump_count >= MAX_PRICE_BUMPS:
        raise DispatchError(
            f"Narxni {MAX_PRICE_BUMPS} martadan ko'p oshirib bo'lmaydi — "
            "iltimos qo'llab-quvvatlash xizmatiga murojaat qiling",
            status_code=409,
        )

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
    order.price_bump_count += 1
    # Qidiruv noldan boshlanadi: avval rad etgan haydovchilarga ham yangi narx bilan
    # qayta taklif chiqishi kerak (`_previously_attempted_driver_ids` DispatchAttempt
    # bo'yicha ishlaydi, shuning uchun eski urinishlar tarixi ham tozalanadi).
    order.dispatch_round = 0
    order.price_bump_requested_at = None
    # "Qidirilmoqda" holatiga qaytarish. Bump paytida order odatda allaqachon PENDING,
    # lekin buni aniq yozib qo'yish shart — WebApp aynan shu statusga qarab qidiruv
    # ko'rsatkichini chizadi va so'rovni davom ettiradi.
    order.status = OrderStatus.PENDING
    await db.execute(
        update(DispatchAttempt)
        .where(
            DispatchAttempt.order_id == order.id,
            DispatchAttempt.status.in_(
                [DispatchAttemptStatus.REJECTED, DispatchAttemptStatus.EXPIRED]
            ),
        )
        .values(status=DispatchAttemptStatus.CANCELLED)
    )
    await db.commit()
    await db.refresh(
        order,
        attribute_names=[
            "price",
            "original_price",
            "price_bump_count",
            "dispatch_round",
            "price_bump_requested_at",
            "status",
            "updated_at",
        ],
    )

    await _dispatch_next(db, order, reason="price_bump")
    return order


async def _notify_sender_driver_found(db: AsyncSession, order: Order, driver: Driver) -> None:
    text = f"✅ '{order.cargo_name}' buyurtmangiz uchun haydovchi topildi! ({driver.truck_number})"
    await notifications.send_telegram_message(order.customer_id, text)
