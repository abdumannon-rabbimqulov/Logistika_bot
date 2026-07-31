"""`WaypointProgressUpdate` sxemasi uchun testlar.

`PATCH /orders/{id}/waypoints/{wp}` da uchraydigan 422 xatolarining bir qismi
so'rov formatidan kelib chiqardi. Bu testlar aynan shu qoidalarni qulflaydi:
qaysi so'rov qabul qilinadi va qaysi biri tushunarli sabab bilan rad etiladi.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from order.models import WaypointStatus
from order.schemas import WaypointProgressUpdate


# ────────────────────────────────────────────────────────────
#  1. Status registri (katta-kichik harf)
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", ["ARRIVED", "arrived", "Arrived", "  arrived  "])
def test_status_accepts_any_case(raw):
    """Klient qanday yozishidan qat'i nazar bir xil natija (ilgari 422 qaytardi)."""
    data = WaypointProgressUpdate(status=raw)
    assert data.status == WaypointStatus.ARRIVED


def test_unknown_status_still_rejected():
    with pytest.raises(ValidationError):
        WaypointProgressUpdate(status="FLYING")


# ────────────────────────────────────────────────────────────
#  2. PENDING — boshlang'ich holat, maqsad sifatida yaroqsiz
# ────────────────────────────────────────────────────────────

def test_pending_rejected_with_readable_message():
    with pytest.raises(ValidationError) as exc:
        WaypointProgressUpdate(status="PENDING")

    message = str(exc.value)
    assert "PENDING" in message
    assert "ARRIVED" in message  # foydalanuvchiga to'g'ri variantlar ko'rsatiladi


@pytest.mark.parametrize("status", ["ARRIVED", "COMPLETED", "SKIPPED"])
def test_valid_target_statuses(status):
    assert WaypointProgressUpdate(status=status).status.value == status


# ────────────────────────────────────────────────────────────
#  3. Koordinatalar
# ────────────────────────────────────────────────────────────

def test_coordinates_accepted_together():
    data = WaypointProgressUpdate(
        status="ARRIVED", latitude=41.311, longitude=69.279, accuracy=12.5
    )
    assert (data.latitude, data.longitude, data.accuracy) == (41.311, 69.279, 12.5)


def test_coordinates_optional():
    """Koordinatasiz ham yuborish mumkin — server Redis'dagi nuqtaga tayanadi."""
    data = WaypointProgressUpdate(status="COMPLETED")
    assert data.latitude is None and data.longitude is None


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "ARRIVED", "latitude": 41.3},
        {"status": "ARRIVED", "longitude": 69.2},
    ],
)
def test_half_coordinate_rejected(payload):
    """Yarim koordinata geofence uchun yaroqsiz — jimgina eski nuqtaga tayanmaslik uchun."""
    with pytest.raises(ValidationError) as exc:
        WaypointProgressUpdate(**payload)
    assert "birga yuborilishi" in str(exc.value)


def test_accuracy_without_coordinates_rejected():
    with pytest.raises(ValidationError):
        WaypointProgressUpdate(status="ARRIVED", accuracy=10)


def test_out_of_range_coordinates_rejected():
    with pytest.raises(ValidationError):
        WaypointProgressUpdate(status="ARRIVED", latitude=120, longitude=69.2)
