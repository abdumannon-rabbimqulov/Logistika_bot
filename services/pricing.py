"""Narxlash biznes qoidalari — masofani yaxlitlash va sender narx tahriri.

Bu yerda uchta qoida jamlangan:

1. **Masofa 5 km qadamiga yaxlitlanadi** (`round_distance_km`). Narx aynan shu
   yaxlitlangan masofadan hisoblanadi — OSRM qaytargan "112.37 km" kabi aniq
   raqam mijozga tushunarsiz narx beradi, 110/115 esa oldindan taxmin qilinadi.

2. **5 ta tayyor narx oshirish tugmasi** (`QUICK_PRICE_INCREMENTS`) — sender
   narxni qo'lda yozmasdan bir bosishda oshira olishi uchun frontend shu
   variantlarni ko'rsatadi.

3. **Qo'lda narx tahriri chegarasi** — narxni oshirish cheklanmagan, lekin
   pasaytirish `PlatformSettings.sender_max_discount_percent` (standart 15%)
   dan oshmasligi kerak. Aks holda haydovchilar uchun narx real bo'lmay qoladi
   va buyurtma umuman qabul qilinmaydi.

Yaxlitlash hamma joyda `Decimal` + `ROUND_HALF_UP` bilan qilinadi: Python'ning
o'rnatilgan `round()` "banker's rounding" ishlatadi va `round(22.5) == 22`
beradi — ya'ni 112.5 km noto'g'ri ravishda 110 km ga tushib qolardi.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from typing import Optional, Union

from sqlalchemy.ext.asyncio import AsyncSession

Number = Union[int, float, Decimal]

# Masofa yaxlitlash qadami (km)
DISTANCE_STEP_KM = 5

# Sender uchun tayyor narx oshirish variantlari (UZS)
QUICK_PRICE_INCREMENTS: tuple[Decimal, ...] = (
    Decimal("100000"),
    Decimal("200000"),
    Decimal("300000"),
    Decimal("400000"),
    Decimal("500000"),
)

# Chegirma chegarasi sozlama sifatida: kalit nomi (admin API/hujjatlar uchun)
# va baza sozlamasi mavjud bo'lmaganda ishlatiladigan standart qiymat.
SENDER_MAX_DISCOUNT_PERCENT_KEY = "SENDER_MAX_DISCOUNT_PERCENT"
DEFAULT_SENDER_MAX_DISCOUNT_PERCENT = Decimal("15")

_CENTS = Decimal("0.01")


class PriceValidationError(ValueError):
    """Sender kiritgan narx biznes qoidalariga mos emas (router 400 ga aylantiradi)."""


def round_distance_km(distance_km: Number) -> int:
    """Masofani eng yaqin 5 km ga yaxlitlaydi: `int(round(distance / 5) * 5)`.

    112 km -> 110, 113 km -> 115, 112.5 km -> 115 (yarim qadam yuqoriga).
    """
    if distance_km is None:
        raise PriceValidationError("Masofa aniqlanmagan")
    value = Decimal(str(distance_km))
    if value < 0:
        raise PriceValidationError("Masofa manfiy bo'lishi mumkin emas")
    step = Decimal(DISTANCE_STEP_KM)
    steps = (value / step).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(steps * step)


def _money(amount: Decimal, rounding: str = ROUND_HALF_UP) -> Decimal:
    return amount.quantize(_CENTS, rounding=rounding)


def min_allowed_price(base_price: Number, max_discount_percent: Number) -> Decimal:
    """Sender tusha oladigan eng past narx: `base_price * (1 - foiz / 100)`.

    Pastga yaxlitlanadi (`ROUND_DOWN`) — aks holda tiyinlar hisobiga chegara
    ozgina yuqoriga siljib, aynan chegaradagi narx rad etilib qolardi.
    """
    base = Decimal(str(base_price))
    percent = Decimal(str(max_discount_percent))
    if base < 0:
        raise PriceValidationError("Asosiy narx manfiy bo'lishi mumkin emas")
    if not (Decimal(0) <= percent <= Decimal(100)):
        raise PriceValidationError("Chegirma foizi 0 va 100 orasida bo'lishi kerak")
    return _money(base * (Decimal(1) - percent / Decimal(100)), rounding=ROUND_DOWN)


def validate_custom_price(
    custom_price: Number,
    base_price: Number,
    max_discount_percent: Number = DEFAULT_SENDER_MAX_DISCOUNT_PERCENT,
) -> Decimal:
    """Sender qo'lda kiritgan narxni tekshiradi va normallashtirilgan holda qaytaradi.

    Oshirish cheklanmagan. Pasaytirish `max_discount_percent` bilan chegaralangan —
    chegaradan past narx `PriceValidationError` ko'taradi.
    """
    price = Decimal(str(custom_price))
    if price <= 0:
        raise PriceValidationError("Narx musbat bo'lishi kerak")

    floor_price = min_allowed_price(base_price, max_discount_percent)
    if price < floor_price:
        raise PriceValidationError(
            f"Narxni {max_discount_percent}% dan ko'proq tushirib bo'lmaydi — "
            f"eng past narx {floor_price} UZS"
        )
    return _money(price)


def quick_price_options(base_price: Number) -> list[dict]:
    """5 ta tayyor "narxni oshirish" varianti (+100 000 ... +500 000 UZS)."""
    base = _money(Decimal(str(base_price)))
    return [
        {"increment": increment, "price": base + increment}
        for increment in QUICK_PRICE_INCREMENTS
    ]


async def get_sender_max_discount_percent(db: AsyncSession) -> Decimal:
    """Chegirma chegarasini tizim sozlamalaridan o'qiydi (yo'q bo'lsa — standart 15%).

    `services.billing` ichida import qilinadi: `billing` modul darajasida
    `pricing` ga bog'liq emas, shuning uchun aylanma import xavfi yo'q.
    """
    from services import billing

    settings = await billing.get_or_create_settings(db)
    percent: Optional[Decimal] = getattr(settings, "sender_max_discount_percent", None)
    if percent is None:
        return DEFAULT_SENDER_MAX_DISCOUNT_PERCENT
    return Decimal(str(percent))


async def validate_custom_price_for_db(
    db: AsyncSession, custom_price: Number, base_price: Number
) -> Decimal:
    """`validate_custom_price`, chegirma foizi bazadagi sozlamadan olinadi."""
    percent = await get_sender_max_discount_percent(db)
    return validate_custom_price(custom_price, base_price, percent)
