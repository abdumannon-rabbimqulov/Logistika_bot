"""Self-hosted OSRM orqali marshrut hisoblash (masofa, davomiylik, geometriya)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

import httpx

from config.config import OSRM_BASE_URL

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 8.0


class OSRMRouteError(Exception):
    """OSRM marshrut hisoblay olmadi (server javob bermadi yoki nuqta yo'ldan uzoq)."""


class OSRMUnavailableError(OSRMRouteError):
    """OSRM serveriga umuman ulanib bo'lmadi — bu BIZNING infratuzilma nosozligimiz.

    Mijozga 503 qaytarilishi kerak: u manzilni o'zgartirib qayta urinsa ham foyda yo'q.
    """


class OSRMNoRouteError(OSRMRouteError):
    """OSRM javob berdi, lekin bu ikki nuqta orasida yo'l topa olmadi.

    Bu mijoz kiritgan ma'lumot muammosi (masalan nuqta yo'ldan juda uzoqda yoki
    dengiz ortida) — 422 qaytariladi, boshqa manzil tanlash yordam beradi.
    """


@dataclass
class RouteResult:
    distance_km: float
    duration_min: float
    geometry_wkt: str  # "LINESTRING(lon lat, lon lat, ...)" — SRID 4326 (PostGIS uchun)
    geometry: list[tuple[float, float]]  # [(latitude, longitude), ...] — xaritada chizish uchun


async def get_route(
    coordinates: Sequence[tuple[float, float]], *, overview: str = "full"
) -> RouteResult:
    """coordinates: ketma-ket (latitude, longitude) juftliklar ro'yxati (kamida 2 ta, pickup->delivery tartibida).

    `overview="full"` — bazaga saqlash uchun to'liq aniqlikdagi geometriya.
    `overview="simplified"` — xaritada ko'rsatish uchun soddalashtirilgan (bir necha marta
    kam nuqta, ya'ni yengilroq JSON javob; ko'z bilan farqi bilinmaydi).
    """
    if len(coordinates) < 2:
        raise OSRMRouteError("Marshrut hisoblash uchun kamida 2 ta nuqta kerak")

    coords_str = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
    url = f"{OSRM_BASE_URL}/route/v1/driving/{coords_str}"
    params = {"overview": overview, "geometries": "geojson"}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("OSRM so'rovi muvaffaqiyatsiz (%s): %s", url, exc)
        raise OSRMUnavailableError(f"OSRM serveriga ulanib bo'lmadi: {exc}") from exc

    if data.get("code") != "Ok" or not data.get("routes"):
        raise OSRMNoRouteError(f"OSRM marshrut topa olmadi: {data.get('code')}")

    route = data["routes"][0]
    distance_km = route["distance"] / 1000
    duration_min = route["duration"] / 60
    line_coords = route["geometry"]["coordinates"]  # [[lon, lat], ...]
    wkt_points = ", ".join(f"{lon} {lat}" for lon, lat in line_coords)

    return RouteResult(
        distance_km=round(distance_km, 2),
        duration_min=round(duration_min, 1),
        geometry_wkt=f"LINESTRING({wkt_points})",
        # WKT (lon lat) dan farqli — bu yerda (lat, lon), chunki xarita kutubxonalari
        # (Yandex Maps) shu tartibda kutadi.
        geometry=[(lat, lon) for lon, lat in line_coords],
    )
