"""Yuk tayyor bo'lish vaqti (`pickup_at`) validatsiyasi.

Mijoz buyurtmani kelajakka rejalashtira oladi ("2 kundan keyin"), lekin:
- o'tmishdagi vaqt qabul qilinmaydi (haydovchi hech qachon yeta olmaydigan buyurtma);
- juda uzoq kelajak ham qabul qilinmaydi (terish xatosi buyurtmani navbatda abadiy
  osilib qolishiga olib kelardi).

Xuddi shu qoida yaratishda ham, TAHRIRLASHDA ham amal qiladi — ilgari `OrderUpdate`
da tekshiruv umuman yo'q edi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from order.schemas import (
    MAX_PICKUP_DAYS_AHEAD,
    OrderUpdate,
    validate_pickup_time,
)


def utc_in(**delta) -> datetime:
    return datetime.now(timezone.utc) + timedelta(**delta)


# ────────────────────────────────────────────────────────────
#  1. Qabul qilinadigan vaqtlar
# ────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("label", "value"),
    [
        ("hozir", utc_in()),
        ("30 soniyadan keyin", utc_in(seconds=30)),
        ("2 soatdan keyin", utc_in(hours=2)),
        ("2 kundan keyin", utc_in(days=2)),
        ("chegaraga yaqin", utc_in(days=MAX_PICKUP_DAYS_AHEAD - 1)),
    ],
)
def test_future_times_accepted(label, value):
    assert validate_pickup_time(value) == value


def test_small_clock_skew_tolerated():
    """Mijoz "hozir" tanlaganda so'rov tarmoqda kechikishi mumkin — 1 daqiqa imtiyoz."""
    assert validate_pickup_time(utc_in(seconds=-30)) is not None


def test_naive_datetime_treated_as_utc():
    """Mintaqasiz qiymat UTC deb qabul qilinadi (DB ustuni `timezone=True`)."""
    naive = (datetime.now(timezone.utc) + timedelta(days=1)).replace(tzinfo=None)
    assert validate_pickup_time(naive) == naive


# ────────────────────────────────────────────────────────────
#  2. Rad etiladigan vaqtlar
# ────────────────────────────────────────────────────────────

def test_past_rejected():
    with pytest.raises(ValueError) as exc:
        validate_pickup_time(utc_in(days=-1))
    assert "o'tmishda" in str(exc.value)


def test_too_far_future_rejected():
    with pytest.raises(ValueError) as exc:
        validate_pickup_time(utc_in(days=MAX_PICKUP_DAYS_AHEAD + 1))
    assert str(MAX_PICKUP_DAYS_AHEAD) in str(exc.value)


# ────────────────────────────────────────────────────────────
#  3. Tahrirlash (regressiya: ilgari bu yerda tekshiruv yo'q edi)
# ────────────────────────────────────────────────────────────

def test_update_rejects_past_pickup():
    with pytest.raises(ValidationError):
        OrderUpdate(pickup_at=utc_in(days=-3))


def test_update_rejects_far_future_pickup():
    with pytest.raises(ValidationError):
        OrderUpdate(pickup_at=utc_in(days=MAX_PICKUP_DAYS_AHEAD + 10))


def test_update_accepts_future_pickup():
    value = utc_in(days=5)
    assert OrderUpdate(pickup_at=value).pickup_at == value


def test_update_without_pickup_is_valid():
    """`pickup_at` ixtiyoriy — boshqa maydonni tahrirlash bloklanmasligi kerak."""
    assert OrderUpdate(cargo_name="Mebel").pickup_at is None
