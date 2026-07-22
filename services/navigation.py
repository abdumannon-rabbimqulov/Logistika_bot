"""Haydovchi uchun tashqi navigatsiya havolalari.

Biz ilova ichida marshrut chizmaymiz — marshrutni haydovchi o'zi odatlangan ilovasida
(Yandex Navigator/Xaritalar, Google Maps) quradi. Bu yerda faqat o'sha ilovalarni
kerakli nuqtalar bilan ochadigan URL tayyorlanadi.

Faqat http(s) havolalar ishlatiladi: ular brauzerda ham ochiladi, mobil qurilmada esa
o'rnatilgan ilova bo'lsa o'sha ilovaga o'tadi. `yandexnavi://` kabi maxsus sxemalar
Telegram inline tugmalarida qo'llab-quvvatlanmaydi, shuning uchun ular ishlatilmaydi.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Protocol, Union

Number = Union[int, float, Decimal]


class HasCoordinates(Protocol):
    """OrderWaypoint kabi latitude/longitude'ga ega har qanday obyekt."""

    latitude: Optional[Number]
    longitude: Optional[Number]


def _coords(point: Optional[HasCoordinates]) -> Optional[tuple[float, float]]:
    if point is None or point.latitude is None or point.longitude is None:
        return None
    return float(point.latitude), float(point.longitude)


def _fmt(lat: float, lon: float) -> str:
    # 6 xona ~11 sm aniqlik — navigatsiya uchun yetarli, URL'ni ham qisqartiradi.
    return f"{lat:.6f},{lon:.6f}"


def yandex_route_url(origin: Optional[HasCoordinates], destination: Optional[HasCoordinates]) -> Optional[str]:
    """Yandex Xaritalar: to'liq marshrut (olib ketish -> yetkazish), avtomobil rejimida."""
    start, end = _coords(origin), _coords(destination)
    if start is None or end is None:
        return None
    return f"https://yandex.uz/maps/?rtext={_fmt(*start)}~{_fmt(*end)}&rtt=auto"


def google_route_url(origin: Optional[HasCoordinates], destination: Optional[HasCoordinates]) -> Optional[str]:
    """Google Maps: to'liq marshrut (olib ketish -> yetkazish), avtomobil rejimida."""
    start, end = _coords(origin), _coords(destination)
    if start is None or end is None:
        return None
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={_fmt(*start)}&destination={_fmt(*end)}&travelmode=driving"
    )


def yandex_point_url(point: Optional[HasCoordinates]) -> Optional[str]:
    """Yandex Xaritalar: bitta nuqtagacha marshrut — boshlanish haydovchining joriy joyi.

    `rtext` ning chap tomoni bo'sh qoldirilsa, Yandex boshlanish nuqtasi sifatida
    foydalanuvchining joriy joylashuvini oladi — haydovchiga aynan shu kerak.
    """
    coords = _coords(point)
    if coords is None:
        return None
    return f"https://yandex.uz/maps/?rtext=~{_fmt(*coords)}&rtt=auto"


def google_point_url(point: Optional[HasCoordinates]) -> Optional[str]:
    """Google Maps: joriy joylashuvdan shu nuqtagacha marshrut (origin berilmagani uchun)."""
    coords = _coords(point)
    if coords is None:
        return None
    return f"https://www.google.com/maps/dir/?api=1&destination={_fmt(*coords)}&travelmode=driving"
