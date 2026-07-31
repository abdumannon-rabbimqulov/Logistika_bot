"""`collect_waypoint_violations` — bitta so'rovga BARCHA sabablar qaytishi.

Ilgari tekshiruvlar birinchi muammoda `raise` qilardi va foydalanuvchi sabablarni
birma-bir kashf etardi. Bu testlar yangi xulqni qulflaydi: hamma amaldagi sabab
bir ro'yxatda, har biri kodi va aniq raqamlari bilan.

Bazaga bog'liq emas — ORM obyektlari xotirada quriladi (`tests/conftest.py` mapper'larni
hal qiladi).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from order.models import Order, OrderStatus, OrderWaypoint, WaypointStatus, WaypointType
from services import geofence, order_flow
from services.problems import Violation, WaypointProblem

# Toshkent (yuk ortish) va Samarqand (yetkazish) — orasi ~270 km, geofence radiusidan
# ancha uzoq, shuning uchun "noto'g'ri joyda" holatini ishonchli beradi.
TASHKENT = (41.311, 69.279)
SAMARKAND = (39.654, 66.959)


def make_waypoint(
    wp_id: int,
    sequence: int,
    wp_type: WaypointType,
    status: WaypointStatus,
    point: tuple[float, float],
    address: str,
) -> OrderWaypoint:
    wp = OrderWaypoint()
    wp.id = wp_id
    wp.sequence = sequence
    wp.type = wp_type
    wp.status = status
    wp.latitude = Decimal(str(point[0]))
    wp.longitude = Decimal(str(point[1]))
    wp.address = address
    return wp


def make_order(*, status=OrderStatus.IN_PROGRESS, driver_id=7, waypoint_statuses=None) -> Order:
    """Ikki nuqtali buyurtma: Toshkent (PICKUP) → Samarqand (DELIVERY)."""
    pickup_status, delivery_status = waypoint_statuses or (
        WaypointStatus.PENDING,
        WaypointStatus.PENDING,
    )
    order = Order()
    order.id = 1
    order.status = status
    order.driver_id = driver_id
    order.waypoints = [
        make_waypoint(1, 1, WaypointType.PICKUP, pickup_status, TASHKENT, "Toshkent, Chilonzor 5"),
        make_waypoint(2, 2, WaypointType.DELIVERY, delivery_status, SAMARKAND, "Samarqand, Registon 1"),
    ]
    return order


def at(point: tuple[float, float], accuracy: float | None = 18.0) -> geofence.DriverCoords:
    return geofence.DriverCoords(latitude=point[0], longitude=point[1], accuracy_m=accuracy)


def codes(violations: list[Violation]) -> set[str]:
    return {v.code for v in violations}


def by_code(violations: list[Violation], code: str) -> Violation:
    match = next((v for v in violations if v.code == code), None)
    assert match is not None, f"{code} topilmadi: {codes(violations)}"
    return match


# ────────────────────────────────────────────────────────────
#  1. To'g'ri so'rov bloklanmasligi kerak (regressiya)
# ────────────────────────────────────────────────────────────

def test_valid_step_has_no_violations():
    order = make_order()
    violations = order_flow.collect_waypoint_violations(
        order, order.waypoints[0], WaypointStatus.ARRIVED, coords=at(TASHKENT)
    )
    assert violations == []


# ────────────────────────────────────────────────────────────
#  2. Asosiy talab: hamma sabab birdan qaytadi
# ────────────────────────────────────────────────────────────

def test_all_reasons_reported_at_once():
    """Buyurtma noaktiv + haydovchi yo'q + noto'g'ri nuqta + noto'g'ri o'tish + uzoq masofa."""
    order = make_order(status=OrderStatus.PENDING, driver_id=None)

    violations = order_flow.collect_waypoint_violations(
        order,
        order.waypoints[1],                 # noto'g'ri nuqta: avval PICKUP yopilishi kerak
        WaypointStatus.COMPLETED,           # PENDING -> COMPLETED taqiqlangan
        coords=at(TASHKENT),                # Samarqand nuqtasidan ~270 km uzoq
    )

    assert codes(violations) == {
        "ORDER_NOT_ACTIVE",
        "NO_DRIVER_ASSIGNED",
        "WRONG_WAYPOINT",
        "INVALID_TRANSITION",
        "GEOFENCE_TOO_FAR",
    }


# ────────────────────────────────────────────────────────────
#  3. Har bir sabab aniq raqamlar bilan
# ────────────────────────────────────────────────────────────

def test_too_far_reports_distance_and_allowed_radius():
    order = make_order()
    violations = order_flow.collect_waypoint_violations(
        order, order.waypoints[0], WaypointStatus.ARRIVED, coords=at(SAMARKAND)
    )

    far = by_code(violations, "GEOFENCE_TOO_FAR")
    assert far.context["distance_m"] > far.context["allowed_radius_m"]
    assert far.context["allowed_radius_m"] >= far.context["base_radius_m"]
    # Foydalanuvchi qancha yaqinlashishi kerakligini matndan ham ko'radi
    assert "ruxsat etilgan radius" in far.message
    assert "yaqinlashing" in far.message


def test_wrong_waypoint_points_to_the_expected_one():
    order = make_order()
    violations = order_flow.collect_waypoint_violations(
        order, order.waypoints[1], WaypointStatus.ARRIVED, coords=at(SAMARKAND)
    )

    wrong = by_code(violations, "WRONG_WAYPOINT")
    assert wrong.context["expected_waypoint_id"] == order.current_waypoint.id == 1
    assert wrong.context["expected_sequence"] == 1
    assert wrong.context["expected_type"] == "PICKUP"
    assert wrong.context["expected_address"] == "Toshkent, Chilonzor 5"


def test_invalid_transition_lists_allowed_statuses_in_uzbek():
    order = make_order()
    violations = order_flow.collect_waypoint_violations(
        order, order.waypoints[0], WaypointStatus.COMPLETED, coords=at(TASHKENT)
    )

    bad = by_code(violations, "INVALID_TRANSITION")
    assert bad.context["from_status"] == "PENDING"
    assert bad.context["to_status"] == "COMPLETED"
    assert bad.context["allowed_statuses"] == ["ARRIVED", "SKIPPED"]
    # Xom enum qiymati emas, o'zbekcha yorliq ko'rsatiladi
    assert "kutilmoqda" in bad.message and "PENDING" not in bad.message


def test_order_not_active_lists_allowed_statuses():
    order = make_order(status=OrderStatus.CANCELLED)
    violations = order_flow.collect_waypoint_violations(
        order, order.waypoints[0], WaypointStatus.ARRIVED, coords=at(TASHKENT)
    )

    inactive = by_code(violations, "ORDER_NOT_ACTIVE")
    assert inactive.context["order_status"] == "CANCELLED"
    assert set(inactive.context["allowed_statuses"]) == {"SCHEDULED", "ACCEPTED", "IN_PROGRESS"}


def test_low_accuracy_reports_limit():
    order = make_order()
    violations = order_flow.collect_waypoint_violations(
        order, order.waypoints[0], WaypointStatus.ARRIVED, coords=at(TASHKENT, accuracy=5000)
    )

    low = by_code(violations, "LOCATION_ACCURACY_LOW")
    assert low.context["accuracy_m"] == 5000
    assert low.context["max_accuracy_m"] < low.context["accuracy_m"]


# ────────────────────────────────────────────────────────────
#  4. Joylashuv va admin override
# ────────────────────────────────────────────────────────────

def test_coords_violation_is_passed_through():
    """Koordinata umuman olinmagan bo'lsa, sabab boshqalarni to'smaydi — ro'yxatga qo'shiladi."""
    order = make_order(status=OrderStatus.CANCELLED)
    unknown = Violation(code="LOCATION_UNKNOWN", message="Joylashuvingiz aniqlanmadi.")

    violations = order_flow.collect_waypoint_violations(
        order,
        order.waypoints[0],
        WaypointStatus.ARRIVED,
        coords=None,
        coords_violation=unknown,
    )

    assert codes(violations) == {"ORDER_NOT_ACTIVE", "LOCATION_UNKNOWN"}


def test_admin_override_skips_geofence_only():
    """Override geofence'ni chetlab o'tadi, lekin ketma-ketlik qoidasini EMAS."""
    order = make_order()
    violations = order_flow.collect_waypoint_violations(
        order,
        order.waypoints[1],
        WaypointStatus.ARRIVED,
        coords=at(SAMARKAND),
        override_reason="GPS ishlamadi",
    )

    assert codes(violations) == {"WRONG_WAYPOINT"}


def test_skip_without_reason():
    order = make_order()
    violations = order_flow.collect_waypoint_violations(
        order, order.waypoints[0], WaypointStatus.SKIPPED, coords=None
    )
    # SKIPPED uchun nuqtaga borish talab qilinmaydi — faqat sabab yetishmayapti
    assert codes(violations) == {"SKIP_REASON_REQUIRED"}


def test_all_waypoints_done():
    order = make_order(
        waypoint_statuses=(WaypointStatus.COMPLETED, WaypointStatus.COMPLETED)
    )
    violations = order_flow.collect_waypoint_violations(
        order, order.waypoints[1], WaypointStatus.ARRIVED, coords=at(SAMARKAND)
    )
    assert "ALL_WAYPOINTS_DONE" in codes(violations)


# ────────────────────────────────────────────────────────────
#  5. HTTP javob shakli
# ────────────────────────────────────────────────────────────

def test_problem_detail_shape():
    problem = WaypointProblem(
        [
            Violation("WRONG_WAYPOINT", "Avval yuk ortish nuqtasini yakunlang.", {"expected_waypoint_id": 1}),
            Violation("GEOFENCE_TOO_FAR", "Siz manzildan 269.1 km uzoqdasiz.", {"distance_m": 269142}),
        ]
    )
    detail = problem.as_detail()

    assert [e["code"] for e in detail["errors"]] == ["WRONG_WAYPOINT", "GEOFENCE_TOO_FAR"]
    assert detail["errors"][0]["expected_waypoint_id"] == 1
    # Birlashtirilgan matnda ikkala sabab ham bor va qo'sh tinish belgisi yo'q
    assert "yakunlang." in detail["message"] and "uzoqdasiz." in detail["message"]
    assert ".;" not in detail["message"]


@pytest.mark.asyncio
async def test_apply_waypoint_progress_raises_problem_with_all_reasons():
    """Servis darajasida ham bitta istisnoda barcha sabablar bo'ladi."""
    order = make_order(status=OrderStatus.PENDING, driver_id=None)

    with pytest.raises(WaypointProblem) as exc:
        await order_flow.apply_waypoint_progress(
            None, order, order.waypoints[1], WaypointStatus.COMPLETED, coords=at(TASHKENT)
        )

    assert len(exc.value.violations) >= 4
    assert "WRONG_WAYPOINT" in {v.code for v in exc.value.violations}
