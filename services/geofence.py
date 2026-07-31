"""Haydovchi buyurtma nuqtasida haqiqatan turganini GPS bo'yicha tekshirish.

Nima uchun kerak: ilgari haydovchi `PATCH /orders/{id}/status` orqali istalgan joydan —
uyda o'tirib, GPS umuman o'chiq holda — buyurtmani `COMPLETED` qila olardi va bu darhol
komissiyani yechardi. Endi har bir waypoint qadami shu modul orqali tekshiriladi.

Koordinata manbai (ustuvorlik tartibida):

1. **So'rov tanasidagi o'lchov** — haydovchi tugmani bosgan paytda olingan yangi nuqta.
   Bu ASOSIY manba, chunki Telegram WebApp fonga o'tganda OS `watchPosition`ni to'xtatadi:
   `useLiveLocation` 30 soniyada bir marta yuboradigan "oxirgi ma'lum nuqta" haydovchi
   ilovani ochgan paytda allaqachon eskirgan bo'lishi mumkin.
2. **Redis'dagi oxirgi jonli nuqta** (`live_location.get_driver_location`) — faqat zaxira,
   va faqat `GEOFENCE_LOCATION_MAX_AGE_SEC` ichida bo'lsa. Eski brauzer/ilova
   koordinata yubormasa ham qadam butunlay bloklanib qolmasligi uchun.

Ruxsat etilgan radius aniqlikka qarab kengayadi:

    effective_radius = GEOFENCE_RADIUS_M + min(accuracy, GEOFENCE_ACCURACY_ALLOWANCE_M)

Sabab: shahar markazida yoki ombor binosi yonida GPS aniqligi 100–300 m gacha tushadi.
Qat'iy radius bunday holatda nuqtada TURGAN haydovchini ham rad etardi. Aniqlikning
o'zi juda yomon bo'lsa (`GEOFENCE_MAX_ACCURACY_M` dan katta) — o'lchov umuman
ishonchsiz, shuning uchun radiusni cheksiz kengaytirish o'rniga rad etiladi.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from config.config import (
    GEOFENCE_ACCURACY_ALLOWANCE_M,
    GEOFENCE_LOCATION_MAX_AGE_SEC,
    GEOFENCE_MAX_ACCURACY_M,
    GEOFENCE_RADIUS_M,
)
from services import live_location
from services.problems import Violation
from utils.geo import calculate_distance_km

logger = logging.getLogger(__name__)


class GeofenceError(Exception):
    """Tekshiruvdan o'tmadi — chaqiruvchi (router) buni 422 qilib qaytaradi.

    Matn to'g'ridan-to'g'ri haydovchiga ko'rsatiladi, shuning uchun o'zbekcha va
    aniq: nima bo'lgani va endi nima qilish kerakligi yozilgan.
    """


@dataclass(frozen=True)
class DriverCoords:
    """Haydovchining bir lahzadagi joylashuvi."""

    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    # "body" — so'rov tanasidagi yangi o'lchov, "live" — Redis'dagi oxirgi ma'lum nuqta.
    source: str = "body"


@dataclass(frozen=True)
class GeofenceResult:
    distance_m: int
    effective_radius_m: int
    accuracy_m: Optional[int]
    latitude: float
    longitude: float
    source: str


def _format_distance(distance_m: float) -> str:
    """Masofani odam o'qiydigan ko'rinishda: yaqin bo'lsa metr, uzoq bo'lsa kilometr."""
    if distance_m < 1000:
        return f"{int(round(distance_m))} m"
    return f"{distance_m / 1000:.1f} km"


async def try_resolve_driver_coords(
    driver_id: Optional[int],
    latitude: Optional[float],
    longitude: Optional[float],
    accuracy_m: Optional[float],
) -> tuple[Optional[DriverCoords], Optional[Violation]]:
    """`resolve_driver_coords` ning yiqilmaydigan varianti.

    Muvaffaqiyatda `(coords, None)`, aks holda `(None, Violation)` qaytaradi —
    chaqiruvchi sababni boshqa sabablar bilan birga yig'a olishi uchun.

    `driver_id` `None` bo'lishi mumkin (buyurtmaga haydovchi biriktirilmagan): u holda
    Redis'dan qidirilmaydi, lekin so'rov tanasidagi koordinata baribir ishlatiladi —
    shunda foydalanuvchi "haydovchi yo'q" bilan birga masofani ham ko'radi.
    """
    if latitude is not None and longitude is not None:
        return (
            DriverCoords(
                latitude=latitude, longitude=longitude, accuracy_m=accuracy_m, source="body"
            ),
            None,
        )

    if driver_id is not None:
        live = await live_location.get_driver_location(driver_id)
        if live and live.get("lat") is not None and live.get("lon") is not None:
            if _is_fresh(live.get("ts")):
                return (
                    DriverCoords(
                        latitude=float(live["lat"]),
                        longitude=float(live["lon"]),
                        accuracy_m=live.get("accuracy"),
                        source="live",
                    ),
                    None,
                )
            logger.info("Haydovchi %s uchun Redis'dagi koordinata eskirgan", driver_id)

    return None, Violation(
        code="LOCATION_UNKNOWN",
        message=(
            "Joylashuvingiz aniqlanmadi. Telefon sozlamalarida GPS'ni yoqing va "
            "ilovaga joylashuv ruxsatini bering, so'ng qayta urinib ko'ring."
        ),
        context={"max_age_sec": GEOFENCE_LOCATION_MAX_AGE_SEC},
    )


async def resolve_driver_coords(
    driver_id: int,
    latitude: Optional[float],
    longitude: Optional[float],
    accuracy_m: Optional[float],
) -> DriverCoords:
    """So'rovdagi koordinatani oladi, bo'lmasa Redis'dagi yangi nuqtaga qaytadi.

    Ikkalasi ham bo'lmasa `GeofenceError` — joylashuvsiz qadamni tasdiqlab bo'lmaydi.
    Bu `try_resolve_driver_coords` ustidagi "yiqiladigan" qobiq.
    """
    coords, violation = await try_resolve_driver_coords(
        driver_id, latitude, longitude, accuracy_m
    )
    if violation is not None:
        raise GeofenceError(violation.message)
    assert coords is not None
    return coords


def _is_fresh(ts_raw: Optional[str]) -> bool:
    """Redis'dagi `ts` (ISO UTC) hali eskirmaganini tekshiradi."""
    if not ts_raw:
        return False
    try:
        ts = datetime.fromisoformat(ts_raw)
    except (TypeError, ValueError):
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age_sec = (datetime.now(timezone.utc) - ts).total_seconds()
    return 0 <= age_sec <= GEOFENCE_LOCATION_MAX_AGE_SEC


def evaluate_at_point(
    coords: DriverCoords,
    target_latitude: Optional[float],
    target_longitude: Optional[float],
) -> tuple[Optional[GeofenceResult], Optional[Violation]]:
    """`verify_at_point` ning yiqilmaydigan varianti: sababni qaytaradi, tashlamaydi.

    Muvaffaqiyatda `(result, None)`, aks holda `(None, Violation)`. Sabab matnida
    aniq raqamlar bo'ladi — masofa VA ruxsat etilgan radius: haydovchi qanchalik
    yaqinlashishi kerakligini bilishi uchun (ilgari faqat masofa aytilardi).
    """
    if target_latitude is None or target_longitude is None:
        # Buyurtma yaratishda har bir nuqta geocode qilinadi, shuning uchun bu holat
        # amalda bo'lmasligi kerak — lekin koordinatasiz nuqtani "tekshirildi" deb
        # o'tkazib yuborish geofence'ni jimgina o'chirib qo'yish bilan barobar.
        return None, Violation(
            code="WAYPOINT_NO_COORDS",
            message="Bu nuqtaning koordinatasi belgilanmagan — administratsiyaga murojaat qiling.",
        )

    if coords.accuracy_m is not None and coords.accuracy_m > GEOFENCE_MAX_ACCURACY_M:
        return None, Violation(
            code="LOCATION_ACCURACY_LOW",
            message=(
                f"GPS aniqligi juda past (±{int(coords.accuracy_m)} m, ruxsat: "
                f"±{GEOFENCE_MAX_ACCURACY_M} m). Ochiq joyga chiqing yoki bir necha "
                "soniya kutib, qayta urinib ko'ring."
            ),
            context={
                "accuracy_m": int(coords.accuracy_m),
                "max_accuracy_m": GEOFENCE_MAX_ACCURACY_M,
            },
        )

    distance_km = calculate_distance_km(
        coords.latitude, coords.longitude, target_latitude, target_longitude
    )
    if distance_km is None:
        # calculate_distance_km koordinatalardan biri None bo'lsa None qaytaradi —
        # yuqoridagi tekshiruvlardan keyin bu yerga tushmasligi kerak, lekin
        # jim o'tkazib yuborilsa tekshiruv umuman ishlamay qolardi.
        return None, Violation(
            code="LOCATION_UNVERIFIABLE",
            message="Joylashuvni tekshirib bo'lmadi — qayta urinib ko'ring.",
        )

    distance_m = distance_km * 1000
    allowance = min(coords.accuracy_m or 0, GEOFENCE_ACCURACY_ALLOWANCE_M)
    effective_radius = GEOFENCE_RADIUS_M + allowance

    if distance_m > effective_radius:
        return None, Violation(
            code="GEOFENCE_TOO_FAR",
            message=(
                f"Siz manzildan {_format_distance(distance_m)} uzoqdasiz "
                f"(ruxsat etilgan radius: {_format_distance(effective_radius)}). "
                f"Yana {_format_distance(distance_m - effective_radius)} yaqinlashing. "
                "GPS noto'g'ri ko'rsatayotgan bo'lsa — administratsiyaga murojaat qiling."
            ),
            context={
                "distance_m": int(round(distance_m)),
                "allowed_radius_m": int(effective_radius),
                "base_radius_m": GEOFENCE_RADIUS_M,
                "accuracy_m": int(coords.accuracy_m) if coords.accuracy_m is not None else None,
                "source": coords.source,
            },
        )

    return (
        GeofenceResult(
            distance_m=int(round(distance_m)),
            effective_radius_m=int(effective_radius),
            accuracy_m=int(coords.accuracy_m) if coords.accuracy_m is not None else None,
            latitude=coords.latitude,
            longitude=coords.longitude,
            source=coords.source,
        ),
        None,
    )


def verify_at_point(
    coords: DriverCoords,
    target_latitude: Optional[float],
    target_longitude: Optional[float],
) -> GeofenceResult:
    """Haydovchi berilgan nuqta atrofidagi radius ichida ekanini tekshiradi.

    Muvaffaqiyatda o'lchov natijasini qaytaradi (u waypointga audit uchun yoziladi),
    aks holda `GeofenceError` tashlaydi. `evaluate_at_point` ustidagi qobiq.
    """
    result, violation = evaluate_at_point(coords, target_latitude, target_longitude)
    if violation is not None:
        raise GeofenceError(violation.message)
    assert result is not None
    return result
