"""Manzilda yukni tushirish sharti (`unloading_mode`) validatsiyasi.

Mijoz uchta variantdan FAQAT BITTASINI tanlaydi va umuman tanlamasligi ham mumkin
(shart ixtiyoriy). Kutish soati esa faqat "bir necha soat" variantiga tegishli:
"o'sha zahoti tushirish" yoniga 5 soat yozilgan buyurtma ziddiyatli bo'lardi —
haydovchi qaysi biriga ishonishini bilmasdi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from order.models import UnloadingMode
from order.schemas import MAX_UNLOADING_WAIT_HOURS, OrderCreate


def order_payload(**extra) -> dict:
    return {
        "cargo_name": "Sinov yuki",
        "weight": 2,
        "pickup_at": datetime.now(timezone.utc) + timedelta(hours=2),
        "required_truck_type_id": 1,
        "waypoints": [
            {"sequence": 1, "type": "PICKUP", "address": "Toshkent, Chilonzor"},
            {"sequence": 2, "type": "DELIVERY", "address": "Toshkent, Yunusobod"},
        ],
        **extra,
    }


def test_unloading_mode_is_optional():
    """Tanlanmagan holat — eng ko'p uchraydigan yo'l, hech qanday shart qo'yilmaydi."""
    order = OrderCreate(**order_payload())
    assert order.unloading_mode is None
    assert order.unloading_wait_hours is None


@pytest.mark.parametrize("mode", list(UnloadingMode))
def test_each_mode_accepted_alone(mode):
    order = OrderCreate(**order_payload(unloading_mode=mode.value))
    assert order.unloading_mode == mode


def test_wait_hours_accepted_with_hours_mode():
    order = OrderCreate(**order_payload(unloading_mode="HOURS", unloading_wait_hours=5))
    assert order.unloading_mode == UnloadingMode.HOURS
    assert order.unloading_wait_hours == 5


def test_hours_mode_without_wait_hours_is_valid():
    """Soat ko'rsatilmasa shart "bir necha soat" bo'lib qolaveradi — bu xato emas."""
    order = OrderCreate(**order_payload(unloading_mode="HOURS"))
    assert order.unloading_wait_hours is None


@pytest.mark.parametrize("mode", ["IMMEDIATE", "DAY"])
def test_wait_hours_rejected_for_other_modes(mode):
    with pytest.raises(ValidationError, match="bir necha soat kutish"):
        OrderCreate(**order_payload(unloading_mode=mode, unloading_wait_hours=5))


def test_wait_hours_without_mode_rejected():
    """Soat bor, variant yo'q — bu ham ziddiyat: qaysi shart ekani noma'lum."""
    with pytest.raises(ValidationError):
        OrderCreate(**order_payload(unloading_wait_hours=5))


@pytest.mark.parametrize("hours", [0, -1, MAX_UNLOADING_WAIT_HOURS + 1])
def test_wait_hours_out_of_range_rejected(hours):
    """Chegaradan oshgan kutish aslida "kun kutish" (`DAY`) varianti."""
    with pytest.raises(ValidationError):
        OrderCreate(**order_payload(unloading_mode="HOURS", unloading_wait_hours=hours))


def test_unknown_mode_rejected():
    with pytest.raises(ValidationError):
        OrderCreate(**order_payload(unloading_mode="WEEK"))
