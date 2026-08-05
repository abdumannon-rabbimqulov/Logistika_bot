"""Menejer javoblarida moliyaviy ma'lumot yo'qligini qulflaydi.

Ikki mexanizm tekshiriladi:

1. `manager/schemas.py` dagi javob sxemalari narx maydonlarini UMUMAN e'lon
   qilmaydi. Kimdir ertaga qulaylik uchun `price` qo'shsa — test yiqiladi.
2. `strip_finance_fields()` umumiy `/orders/...` javoblaridan o'sha kalitlarni
   olib tashlaydi (ichma-ich joylashgan obyektlardan ham).

Uchinchi qavat — `support_service` bazasida moliyaviy ustun yo'qligi — shu yerda
tekshirilmaydi, chunki u alohida paket va o'z image'ida yashaydi; uning modeli
narxni saqlash imkoniyatiga ega emas (`support_service/models.py`).
"""

from __future__ import annotations

import pytest

from manager import schemas as manager_schemas
from order import schemas as order_schemas

# Menejer hech qachon ko'rmasligi kerak bo'lgan kalitlar.
FORBIDDEN = [
    "price",
    "base_price",
    "original_price",
    "currency",
    "billable_distance_km",
    "price_bump_count",
    "price_bump_requested_at",
]


@pytest.mark.parametrize("field", FORBIDDEN)
@pytest.mark.parametrize(
    "schema",
    [
        manager_schemas.ManagerOrderDetail,
        manager_schemas.ManagerOrderListItem,
        manager_schemas.AvailableTruck,
    ],
)
def test_manager_schemas_have_no_finance_fields(schema, field):
    assert field not in schema.model_fields, (
        f"{schema.__name__} sxemasiga moliyaviy maydon '{field}' qo'shilgan — "
        "menejer narxni ko'rmasligi kerak"
    )


def test_forbidden_fields_are_all_listed_in_finance_fields():
    """`FINANCE_FIELDS` to'plami tozalash uchun ishlatiladi — to'liq bo'lsin."""
    missing = [f for f in FORBIDDEN if f not in manager_schemas.FINANCE_FIELDS]
    assert not missing, f"FINANCE_FIELDS ga qo'shilmagan: {missing}"


def test_order_response_still_has_price_for_others():
    """Nazorat testi: narx boshqa rollar uchun JOYIDA qoladi.

    Aks holda "moliya yopiq" testlari sxema bo'shab qolgani uchun ham o'tib
    ketaverardi va hech narsani isbotlamasdi.
    """
    assert "price" in order_schemas.OrderResponse.model_fields
    assert "price" in order_schemas.OrderListItem.model_fields


def test_strip_finance_fields_removes_top_level_keys():
    payload = {"id": 1, "cargo_name": "Paxta", "price": "500000", "currency": "UZS"}
    cleaned = manager_schemas.strip_finance_fields(payload)
    assert cleaned == {"id": 1, "cargo_name": "Paxta"}


def test_strip_finance_fields_is_recursive():
    payload = {
        "id": 1,
        "price": 100,
        "waypoints": [{"id": 5, "price": 10, "address": "Toshkent"}],
        "meta": {"nested": {"base_price": 7, "keep": True}},
    }
    cleaned = manager_schemas.strip_finance_fields(payload)

    assert "price" not in cleaned
    assert cleaned["waypoints"] == [{"id": 5, "address": "Toshkent"}]
    assert cleaned["meta"]["nested"] == {"keep": True}


def test_strip_finance_fields_keeps_non_finance_data():
    payload = {"id": 1, "status": "in_progress", "driver_id": 3, "total_distance_km": 120}
    assert manager_schemas.strip_finance_fields(payload) == payload
