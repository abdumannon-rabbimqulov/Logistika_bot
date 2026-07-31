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
from services.problems import Violation, WaypointProblem

logger = logging.getLogger(__name__)


class OrderFlowError(Exception):
    """Qoidaga zid o'tish. Matn to'g'ridan-to'g'ri foydalanuvchiga ko'rsatiladi.

    `middlewares/error_handler.py` da global handler bilan **400 Bad Request** ga
    aylantiriladi. Shu sababli har bir endpointda alohida `try/except` yozish shart
    emas: ilgari `Admin_panel/router.py` da aynan shunday tutib olinmagan chaqiruv
    bor edi va u 500 Internal Server Error berardi.
    """

    #: Xato javobidagi mashina o'qiy oladigan kod.
    code = "ORDER_FLOW_ERROR"

    def context(self) -> dict:
        """Xato javobiga qo'shiladigan qo'shimcha qiymatlar (kichik sinflar to'ldiradi)."""
        return {}


class OrderTransitionError(OrderFlowError):
    """Buyurtma statusini bu ketma-ketlikda o'zgartirib bo'lmaydi.

    Masalan `ACCEPTED → COMPLETED`: yuk ortilmasdan yakunlangan bo'lib qolardi
    (va komissiya yechilardi), shuning uchun avval `IN_PROGRESS` bo'lishi shart.
    """

    code = "INVALID_ORDER_TRANSITION"

    def __init__(self, current: OrderStatus, new: OrderStatus):
        self.current = current
        self.new = new
        self.allowed = sorted(s.value for s in ALLOWED_ORDER_TRANSITIONS.get(current, set()))
        super().__init__(
            f"'{_ORDER_STATUS_LABEL.get(current, current.value)}' holatidan "
            f"'{_ORDER_STATUS_LABEL.get(new, new.value)}' holatiga o'tish mumkin emas. "
            "Iltimos, statuslarni ketma-ketlikda o'zgartiring."
        )

    def context(self) -> dict:
        return {
            "current_status": self.current.value,
            "new_status": self.new.value,
            # Shu holatdan qaysi holatlarga o'tsa bo'ladi — mijoz to'g'ri qadamni
            # o'zi tanlay olishi uchun.
            "allowed_statuses": self.allowed,
        }


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

# Nuqta holatlarining o'zbekcha nomlari. Xato matnida xom enum qiymati
# ("'PENDING' holatidan 'ARRIVED' holatiga") o'rniga ishlatiladi.
_WAYPOINT_STATUS_LABEL = {
    WaypointStatus.PENDING: "kutilmoqda",
    WaypointStatus.ARRIVED: "yetib keldi",
    WaypointStatus.COMPLETED: "yakunlandi",
    WaypointStatus.SKIPPED: "o'tkazib yuborildi",
}


def _waypoint_status_label(status: WaypointStatus) -> str:
    return _WAYPOINT_STATUS_LABEL.get(status, status.value)


def ensure_order_transition_allowed(current: OrderStatus, new: OrderStatus) -> None:
    """Buyurtma holati o'tishini tekshiradi; nomaqbul bo'lsa `OrderTransitionError`."""
    if current == new:
        return
    if new not in ALLOWED_ORDER_TRANSITIONS.get(current, set()):
        raise OrderTransitionError(current, new)


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
            f"Bu nuqtani '{_waypoint_status_label(waypoint.status)}' holatidan "
            f"'{_waypoint_status_label(new_status)}' holatiga o'tkazib bo'lmaydi."
        )


def collect_waypoint_violations(
    order: Order,
    waypoint: OrderWaypoint,
    new_status: WaypointStatus,
    *,
    coords: Optional[geofence.DriverCoords],
    coords_violation: Optional[Violation] = None,
    override_reason: Optional[str] = None,
) -> list[Violation]:
    """Qadamni bajarishga to'sqinlik qilayotgan BARCHA sabablarni yig'adi.

    Ilgari har bir tekshiruv birinchi muammoda darhol `raise` qilardi va foydalanuvchi
    sabablarni birma-bir kashf etardi. Bu funksiya bir-biriga bog'liq bo'lmagan hamma
    tekshiruvni oxirigacha bajaradi — masalan noto'g'ri nuqta yuborilgan bo'lsa ham
    masofa baribir o'lchanadi, chunki ikkalasi ham foydalanuvchiga kerak.

    Bo'sh ro'yxat = qadamni bajarish mumkin.
    """
    violations: list[Violation] = []
    is_override = bool(override_reason)

    # ── Buyurtma darajasidagi shartlar ────────────────────────────────────────
    if order.status not in _ACTIVE_ORDER_STATUSES:
        violations.append(
            Violation(
                code="ORDER_NOT_ACTIVE",
                message=(
                    f"Buyurtma '{_ORDER_STATUS_LABEL.get(order.status, order.status.value)}' "
                    "holatida — nuqtalarni belgilab bo'lmaydi."
                ),
                context={
                    "order_status": order.status.value,
                    "allowed_statuses": [s.value for s in _ACTIVE_ORDER_STATUSES],
                },
            )
        )

    if order.driver_id is None:
        violations.append(
            Violation(
                code="NO_DRIVER_ASSIGNED",
                message="Buyurtmaga haydovchi biriktirilmagan — qadamni belgilab bo'lmaydi.",
            )
        )

    # ── Ketma-ketlik: faqat joriy nuqta ustida ish olib boriladi ──────────────
    current = order.current_waypoint
    if current is None:
        violations.append(
            Violation(
                code="ALL_WAYPOINTS_DONE",
                message="Buyurtmaning barcha nuqtalari allaqachon yakunlangan.",
            )
        )
    elif current.id != waypoint.id:
        violations.append(
            Violation(
                code="WRONG_WAYPOINT",
                message=(
                    f"Avval {waypoint_label(current)}ni yakunlang "
                    f"({current.address or 'manzil ko‘rsatilmagan'})."
                ),
                context={
                    "expected_waypoint_id": current.id,
                    "expected_sequence": current.sequence,
                    "expected_type": current.type.value,
                    "expected_address": current.address,
                },
            )
        )

    # ── Nuqta holati o'tishi ──────────────────────────────────────────────────
    allowed = _ALLOWED_WAYPOINT_TRANSITIONS.get(waypoint.status, set())
    if new_status not in allowed:
        violations.append(
            Violation(
                code="INVALID_TRANSITION",
                message=(
                    f"Bu nuqtani '{_waypoint_status_label(waypoint.status)}' holatidan "
                    f"'{_waypoint_status_label(new_status)}' holatiga o'tkazib bo'lmaydi."
                ),
                context={
                    "from_status": waypoint.status.value,
                    "to_status": new_status.value,
                    "allowed_statuses": sorted(s.value for s in allowed),
                },
            )
        )

    # ── Nuqtani tashlab ketish faqat sabab bilan ──────────────────────────────
    if new_status == WaypointStatus.SKIPPED and not is_override:
        violations.append(
            Violation(
                code="SKIP_REASON_REQUIRED",
                message="Nuqtani tashlab ketish uchun sabab (override_reason) ko'rsatilishi shart.",
            )
        )

    # ── Geofence ──────────────────────────────────────────────────────────────
    # Admin qo'lda tasdiqlayotgan bo'lsa (override) joylashuv tekshirilmaydi, va
    # SKIPPED da ham nuqtaga borish talab qilinmaydi.
    if not is_override and new_status != WaypointStatus.SKIPPED:
        if coords_violation is not None:
            violations.append(coords_violation)
        elif coords is None:
            violations.append(
                Violation(
                    code="LOCATION_UNKNOWN",
                    message="Joylashuv aniqlanmadi — qayta urinib ko'ring.",
                )
            )
        else:
            _, geo_violation = geofence.evaluate_at_point(
                coords,
                float(waypoint.latitude) if waypoint.latitude is not None else None,
                float(waypoint.longitude) if waypoint.longitude is not None else None,
            )
            if geo_violation is not None:
                violations.append(geo_violation)

    return violations


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
    coords_violation: Optional[Violation] = None,
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
    # Barcha tekshiruvlar BIR MARTADA — foydalanuvchi sabablarni birma-bir emas,
    # hammasini birdan ko'radi (services/problems.py).
    violations = collect_waypoint_violations(
        order,
        waypoint,
        new_status,
        coords=coords,
        coords_violation=coords_violation,
        override_reason=override_reason,
    )
    if violations:
        raise WaypointProblem(violations)

    is_override = bool(override_reason)
    now = datetime.now(timezone.utc)

    if is_override:
        waypoint.override_by_user_id = override_by_user_id
        waypoint.override_reason = override_reason
    elif new_status != WaypointStatus.SKIPPED:
        # Yuqoridagi yig'uvchi geofence'ni allaqachon tekshirdi va o'tdi — bu yerda
        # faqat audit qiymatlarini olish uchun qayta hisoblanadi (sof funksiya).
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
