"""services/pricing.py biznes qoidalari uchun unit testlar.

Bu testlar bazaga bog'liq emas — `pricing` modulidagi sof funksiyalar tekshiriladi.
Ishga tushirish: `pytest tests/`
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from services.pricing import (
    DEFAULT_SENDER_MAX_DISCOUNT_PERCENT,
    QUICK_PRICE_INCREMENTS,
    PriceValidationError,
    min_allowed_price,
    quick_price_options,
    round_distance_km,
    validate_custom_price,
)


# ────────────────────────────────────────────────────────────
#  1. Masofani 5 km qadamiga yaxlitlash
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("distance", "expected"),
    [
        (112, 110),      # pastga
        (113, 115),      # yuqoriga
        (112.5, 115),    # aynan yarim qadam — YUQORIGA (banker's rounding emas)
        (117.5, 120),    # yarim qadam, juft bo'lmagan tomonda ham yuqoriga
        (110, 110),      # aynan qadamda — o'zgarmaydi
        (0, 0),
        (1, 0),          # 2.5 km dan kam — 0 ga tushadi
        (2.5, 5),
        (2.49, 0),
        (0.4, 0),
        (999.9, 1000),
    ],
)
def test_round_distance_km(distance, expected):
    assert round_distance_km(distance) == expected


def test_round_distance_km_accepts_decimal_and_str_safe_floats():
    # Decimal orqali o'tkazilganda ham float aniqlik xatosi yuzaga kelmasligi kerak
    assert round_distance_km(Decimal("112.5")) == 115
    assert round_distance_km(Decimal("112.4999")) == 110


def test_round_distance_km_returns_int():
    assert isinstance(round_distance_km(Decimal("113.7")), int)


def test_round_distance_km_rejects_negative():
    with pytest.raises(PriceValidationError):
        round_distance_km(-5)


def test_round_distance_km_rejects_none():
    with pytest.raises(PriceValidationError):
        round_distance_km(None)


def test_truck_type_price_uses_rounded_distance():
    """TruckType.calculate_price masofani yaxlitlangan holda ishlatadi."""
    from driver.models import TruckType

    tt = TruckType(base_price=Decimal("50000"), price_per_km=Decimal("1000"), min_price=None)
    # 112 km -> 110 km: 50 000 + 110 * 1 000
    assert tt.calculate_price(Decimal("112")) == Decimal("160000")
    # 113 km -> 115 km: 50 000 + 115 * 1 000
    assert tt.calculate_price(Decimal("113")) == Decimal("165000")
    # 112.5 km -> 115 km (yarim qadam yuqoriga)
    assert tt.calculate_price(Decimal("112.5")) == Decimal("165000")


def test_truck_type_price_respects_min_price():
    from driver.models import TruckType

    tt = TruckType(base_price=Decimal("0"), price_per_km=Decimal("1000"), min_price=Decimal("80000"))
    assert tt.calculate_price(Decimal("3")) == Decimal("80000")


# ────────────────────────────────────────────────────────────
#  2. 5 ta tayyor narx oshirish varianti
# ────────────────────────────────────────────────────────────

def test_quick_price_options_count_and_increments():
    options = quick_price_options(Decimal("500000"))
    assert len(options) == 5
    assert [o["increment"] for o in options] == list(QUICK_PRICE_INCREMENTS)
    assert [o["increment"] for o in options] == [
        Decimal("100000"),
        Decimal("200000"),
        Decimal("300000"),
        Decimal("400000"),
        Decimal("500000"),
    ]


def test_quick_price_options_prices_are_base_plus_increment():
    base = Decimal("750000")
    for option in quick_price_options(base):
        assert option["price"] == base + option["increment"]


def test_quick_price_options_accepts_float_base():
    options = quick_price_options(160000.0)
    assert options[0]["price"] == Decimal("260000.00")


# ────────────────────────────────────────────────────────────
#  3. Qo'lda narx tahriri va chegirma chegarasi
# ────────────────────────────────────────────────────────────

def test_default_discount_percent_is_15():
    assert DEFAULT_SENDER_MAX_DISCOUNT_PERCENT == Decimal("15")


def test_min_allowed_price_default_15_percent():
    assert min_allowed_price(Decimal("1000000"), Decimal("15")) == Decimal("850000.00")


def test_min_allowed_price_rounds_down():
    # 999 999 * 0.85 = 849 999.15 -> pastga yaxlitlanadi, chegara yuqoriga siljimaydi
    assert min_allowed_price(Decimal("999999"), Decimal("15")) == Decimal("849999.15")


def test_min_allowed_price_zero_percent_equals_base():
    assert min_allowed_price(Decimal("500000"), Decimal("0")) == Decimal("500000.00")


def test_min_allowed_price_rejects_out_of_range_percent():
    with pytest.raises(PriceValidationError):
        min_allowed_price(Decimal("100000"), Decimal("101"))
    with pytest.raises(PriceValidationError):
        min_allowed_price(Decimal("100000"), Decimal("-1"))


def test_price_increase_is_unlimited():
    base = Decimal("1000000")
    for multiplier in ("1.01", "2", "10", "1000"):
        price = base * Decimal(multiplier)
        assert validate_custom_price(price, base) == price.quantize(Decimal("0.01"))


def test_price_decrease_within_limit_is_allowed():
    base = Decimal("1000000")
    assert validate_custom_price(Decimal("900000"), base) == Decimal("900000.00")


def test_price_exactly_at_discount_limit_is_allowed():
    base = Decimal("1000000")
    assert validate_custom_price(Decimal("850000"), base) == Decimal("850000.00")


def test_price_below_discount_limit_is_rejected():
    base = Decimal("1000000")
    with pytest.raises(PriceValidationError):
        validate_custom_price(Decimal("849999.99"), base)


def test_custom_discount_percent_from_settings():
    base = Decimal("1000000")
    # Sozlama 25% ga o'zgartirilsa, 800 000 endi ruxsat etiladi
    assert validate_custom_price(Decimal("800000"), base, Decimal("25")) == Decimal("800000.00")
    with pytest.raises(PriceValidationError):
        validate_custom_price(Decimal("749999"), base, Decimal("25"))


def test_zero_discount_percent_forbids_any_decrease():
    base = Decimal("1000000")
    assert validate_custom_price(base, base, Decimal("0")) == Decimal("1000000.00")
    with pytest.raises(PriceValidationError):
        validate_custom_price(Decimal("999999"), base, Decimal("0"))


@pytest.mark.parametrize("bad_price", [Decimal("0"), Decimal("-1"), Decimal("-100000")])
def test_non_positive_price_is_rejected(bad_price):
    with pytest.raises(PriceValidationError):
        validate_custom_price(bad_price, Decimal("1000000"))


def test_error_message_mentions_limit():
    with pytest.raises(PriceValidationError) as exc:
        validate_custom_price(Decimal("100"), Decimal("1000000"))
    assert "850000.00" in str(exc.value)


def test_validation_error_is_value_error():
    """Router `ValueError` ushlagan eski joylar ham buzilmasligi uchun."""
    assert issubclass(PriceValidationError, ValueError)


def test_quick_options_stay_above_discount_floor():
    """Tayyor variantlar narxni oshiradi — hech biri chegaradan past bo'lmaydi."""
    base = Decimal("1000000")
    floor = min_allowed_price(base, DEFAULT_SENDER_MAX_DISCOUNT_PERCENT)
    for option in quick_price_options(base):
        assert option["price"] > floor
        assert validate_custom_price(option["price"], base) == option["price"]
