"""Buyurtma va uning nuqtalari (waypoint) holat mashinasi.

Ilgari buyurtma oqimi FAQAT frontendda mavjud edi: `DriverActiveOrderPage` ikkita tugma
ko'rsatardi (`ACCEPTED → IN_PROGRESS → COMPLETED`), server esa hech narsani tekshirmasdi —
istalgan statusdan istalganiga o'tish mumkin edi, jumladan `COMPLETED → PENDING → COMPLETED`
qilib komissiyani qayta-qayta yechish ham.

Endi batafsillik nuqtalar darajasida yuritiladi (model allaqachon shunga mo'ljallangan) va
`Order.status` ulardan KELIB CHIQADI:

    Waypoint #1 PICKUP    PENDING → ARRIVED → COMPLETED ─┐ birinchi PICKUP yopilishi
    Waypoint #2 TRANSIT   PENDING → ARRIVED → COMPLETED  │   → order IN_PROGRESS
    Waypoint #3 DELIVERY  PENDING → ARRIVED → COMPLETED ─┘ oxirgisi yopilishi
                                                           → order COMPLETED (+komissiya)

Bu yondashuvning yutug'i — ko'p nuqtali (TRANSIT) yuklar qo'shimcha kodsiz qo'llab-quvvatlanadi:
oqim nuqtalar ro'yxati bo'yicha yuradi, ularning soni 2 ta yoki 5 ta bo'lishi ahamiyatsiz.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from order.models import Order, OrderStatus, OrderWaypoint, WaypointStatus, WaypointType
from services import geofence

logger = logging.getLogger(__name__)


class OrderFlowError(Exception):
    """Qoidaga zid o'tish — router buni 422 qilib qaytaradi (matn foydalanuvchiga ko'rinadi)."""


# ── Buyurtma holatlari ────────────────────────────────────────────────────────
# Ilgari bunday jadval umuman yo'q edi va `update_order_status` har qanday o'tishni
# qabul qilardi. COMPLETED va CANCELLED — terminal: bu komissiyani takroran yechish
# yo'lini yopadi (COMPLETED → PENDING → COMPLETED ketma-ketligi endi mumkin emas).
ALLOWED_ORDER_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.SCHEDULED, OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    # SCHEDULED -> IN_PROGRESS: haydovchi belgilangan vaqtdan oldin yetib kelib yukni
    # ortib qo'ysa (yoki admin qadamni qo'lda tasdiqlasa) — kutish holatida qotib qolmasin.
    OrderStatus.SCHEDULED: {
        OrderStatus.ACCEPTED,
        OrderStatus.IN_PROGRESS,
        OrderStatus.PENDING,
        OrderStatus.CANCELLED,
    },
    OrderStatus.ACCEPTED: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED},
    OrderStatus.IN_PROGRESS: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}

# Nuqta ustida ish olib borish mumkin bo'lgan buyurtma holatlari. SCHEDULED ham kiradi:
# haydovchi belgilangan vaqtdan oldin yetib kelishi mumkin va uni "hali vaqt bo'lmadi"
# deb to'sib qo'yish noto'g'ri bo'lardi — geofence baribir joyida ekanini tekshiradi.
_ACTIVE_ORDER_STATUSES = {OrderStatus.SCHEDULED, OrderStatus.ACCEPTED, OrderStatus.IN_PROGRESS}

# Nuqta holatlari: qaysi holatdan qaysisiga o'tish mumkin.
_ALLOWED_WAYPOINT_TRANSITIONS: dict[WaypointStatus, set[WaypointStatus]] = {
    WaypointStatus.PENDING: {WaypointStatus.ARRIVED, WaypointStatus.SKIPPED},
    WaypointStatus.ARRIVED: {WaypointStatus.COMPLETED, WaypointStatus.SKIPPED},
    WaypointStatus.COMPLETED: set(),
    WaypointStatus.SKIPPED: set(),
}

_ORDER_STATUS_LABEL = {
    OrderStatus.SCHEDULED: "rejalashtirilgan",
    OrderStatus.PENDING: "haydovchi qidirilmoqda",
    OrderStatus.ACCEPTED: "qabul qilingan",
    OrderStatus.IN_PROGRESS: "yo'lda",
    OrderStatus.COMPLETED: "yakunlangan",
    OrderStatus.CANCELLED: "bekor qilingan",
}


def ensure_order_transition_allowed(current: OrderStatus, new: OrderStatus) -> None:
    """Buyurtma holati o'tishini tekshiradi; nomaqbul bo'lsa `OrderFlowError`."""
    if current == new:
        return
    if new not in ALLOWED_ORDER_TRANSITIONS.get(current, set()):
        raise OrderFlowError(
            f"'{_ORDER_STATUS_LABEL.get(current, current.value)}' holatidan "
            f"'{_ORDER_STATUS_LABEL.get(new, new.value)}' holatiga o'tish mumkin emas."
        )


def waypoint_label(waypoint: OrderWaypoint) -> str:
    return {
        WaypointType.PICKUP: "yuk ortish nuqtasi",
        WaypointType.DELIVERY: "yetkazish nuqtasi",
        WaypointType.TRANSIT: "oraliq nuqta",
    }.get(waypoint.type, "nuqta")


def ensure_waypoint_actionable(order: Order, waypoint: OrderWaypoint) -> None:
    """Nuqta ayni paytda o'zgartirilishi mumkinligini tekshiradi.

    Eng muhim qoida — KETMA-KETLIK: faqat `order.current_waypoint` ustida ish olib borish
    mumkin. Aks holda haydovchi yuk ortish nuqtasiga bormasdan turib to'g'ridan-to'g'ri
    yetkazish nuqtasini yopib, buyurtmani (va komissiyani) yakunlab yuborardi.
    """
    if order.status not in _ACTIVE_ORDER_STATUSES:
        raise OrderFlowError(
            f"Buyurtma '{_ORDER_STATUS_LABEL.get(order.status, order.status.value)}' holatida — "
            "nuqtalarni belgilab bo'lmaydi."
        )

    current = order.current_waypoint
    if current is None:
        raise OrderFlowError("Buyurtmaning barcha nuqtalari allaqachon yakunlangan.")

    if current.id != waypoint.id:
        raise OrderFlowError(
            f"Avval {waypoint_label(current)}ni yakunlang "
            f"({current.address or 'manzil ko‘rsatilmagan'})."
        )


def ensure_waypoint_transition_allowed(
    waypoint: OrderWaypoint, new_status: WaypointStatus
) -> None:
    if new_status not in _ALLOWED_WAYPOINT_TRANSITIONS.get(waypoint.status, set()):
        raise OrderFlowError(
            f"Bu nuqtani '{waypoint.status.value}' holatidan '{new_status.value}' "
            "holatiga o'tkazib bo'lmaydi."
        )


def next_order_status(order: Order) -> Optional[OrderStatus]:
    """Nuqtalar holatidan kelib chiqib buyurtmaning yangi holatini aniqlaydi.

    `None` — o'zgarish kerak emas. Faqat OLDINGA yo'nalishdagi o'tish qaytariladi:
    - barcha nuqtalar yopilgan (COMPLETED/SKIPPED) → COMPLETED
    - kamida bitta PICKUP yopilgan (yuk ortilgan) → IN_PROGRESS
    """
    waypoints = order.waypoints
    if not waypoints:
        return None

    closed = {WaypointStatus.COMPLETED, WaypointStatus.SKIPPED}

    if all(wp.status in closed for wp in waypoints):
        return OrderStatus.COMPLETED if order.status != OrderStatus.COMPLETED else None

    pickup_done = any(
        wp.type == WaypointType.PICKUP and wp.status == WaypointStatus.COMPLETED
        for wp in waypoints
    )
    if pickup_done and order.status in (OrderStatus.ACCEPTED, OrderStatus.SCHEDULED):
        return OrderStatus.IN_PROGRESS

    # Haydovchi rejalashtirilgan vaqtdan oldin ishga kirishdi (masalan nuqtaga yetib keldi) —
    # buyurtma endi "kutmoqda" emas, faol.
    if order.status == OrderStatus.SCHEDULED and any(
        wp.status != WaypointStatus.PENDING for wp in waypoints
    ):
        return OrderStatus.ACCEPTED

    return None


async def apply_waypoint_progress(
    db: AsyncSession,
    order: Order,
    waypoint: OrderWaypoint,
    new_status: WaypointStatus,
    *,
    coords: Optional[geofence.DriverCoords],
    override_by_user_id: Optional[int] = None,
    override_reason: Optional[str] = None,
) -> Order:
    """Nuqtani yangi holatga o'tkazadi va buyurtma holatini shunga moslaydi.

    `override_reason` berilgan bo'lsa (faqat admin) — geofence tekshiruvi o'tkazib
    yuboriladi, lekin kim va nima sababdan chetlab o'tgani nuqtaga yoziladi. Aks holda
    haydovchi nuqta atrofidagi radiusda ekani majburiy tekshiriladi.

    DIQQAT: buyurtma COMPLETED ga o'tishi `order.crud.update_order_status` orqali bajariladi —
    `completed_at` va `billing.charge_order_commission` o'sha yerda, bitta joyda qoladi.
    """
    ensure_waypoint_actionable(order, waypoint)
    ensure_waypoint_transition_allowed(waypoint, new_status)

    is_override = bool(override_reason)
    now = datetime.now(timezone.utc)

    if is_override:
        waypoint.override_by_user_id = override_by_user_id
        waypoint.override_reason = override_reason
    elif new_status != WaypointStatus.SKIPPED:
        # SKIPPED faqat admin tomonidan (override bilan) qo'yiladi — pastdagi routerda
        # ham tekshiriladi, shuning uchun bu yerga geofence'siz tushmaydi.
        if coords is None:
            raise OrderFlowError("Joylashuv aniqlanmadi — qayta urinib ko'ring.")
        result = geofence.verify_at_point(
            coords,
            float(waypoint.latitude) if waypoint.latitude is not None else None,
            float(waypoint.longitude) if waypoint.longitude is not None else None,
        )
        waypoint.confirmed_latitude = result.latitude
        waypoint.confirmed_longitude = result.longitude
        waypoint.confirmed_distance_m = result.distance_m
        waypoint.confirmed_accuracy_m = result.accuracy_m

    waypoint.status = new_status
    if new_status == WaypointStatus.ARRIVED:
        waypoint.arrived_at = now
    elif new_status in (WaypointStatus.COMPLETED, WaypointStatus.SKIPPED):
        waypoint.completed_at = now
        # "Yetib keldim"ni bosmasdan to'g'ridan-to'g'ri yopish holati bo'lmasligi kerak,
        # lekin admin override qilsa bo'lishi mumkin — vaqt bo'sh qolmasin.
        if waypoint.arrived_at is None:
            waypoint.arrived_at = now

    await db.commit()
    await db.refresh(order, attribute_names=["waypoints", "status", "updated_at"])

    # Nuqtalar o'zgargach buyurtma holati qayta hisoblanadi.
    target = next_order_status(order)
    if target is not None:
        from order import crud  # aylanma importni oldini olish uchun shu yerda

        order = await crud.update_order_status(db, order, target)

    return order
