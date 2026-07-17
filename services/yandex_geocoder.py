"""Yandex Geocoder API orqali manzil qidirish (forward) va aniqlash (reverse)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from config.config import API_YANDEX_KEY

logger = logging.getLogger(__name__)

GEOCODER_URL = "https://geocode-maps.yandex.ru/1.x/"
REQUEST_TIMEOUT = 5.0


@dataclass
class GeocodeResult:
    address: str
    latitude: float
    longitude: float


async def _request(params: dict) -> Optional[dict]:
    if not API_YANDEX_KEY:
        logger.warning("API_YANDEX_KEY sozlanmagan — geocoding ishlamaydi")
        return None

    query = {"apikey": API_YANDEX_KEY, "format": "json", **params}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(GEOCODER_URL, params=query)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Yandex Geocoder so'rovi muvaffaqiyatsiz: %s", exc)
        return None


def _parse_members(data: dict) -> list[GeocodeResult]:
    results: list[GeocodeResult] = []
    members = (
        data.get("response", {})
        .get("GeoObjectCollection", {})
        .get("featureMember", [])
    )
    for member in members:
        geo_object = member.get("GeoObject", {})
        pos = geo_object.get("Point", {}).get("pos")
        if not pos:
            continue
        lon_str, lat_str = pos.split()
        address = (
            geo_object.get("metaDataProperty", {})
            .get("GeocoderMetaData", {})
            .get("text")
            or geo_object.get("name")
            or ""
        )
        results.append(GeocodeResult(address=address, latitude=float(lat_str), longitude=float(lon_str)))
    return results


async def search_address(query: str, *, limit: int = 5) -> list[GeocodeResult]:
    """Matn bo'yicha manzil qidirish — sender manzil kiritganda (autocomplete/tanlash uchun)."""
    if not query or not query.strip():
        return []
    data = await _request({"geocode": query.strip(), "results": limit, "lang": "uz_UZ"})
    if not data:
        return []
    return _parse_members(data)


async def reverse_geocode(latitude: float, longitude: float) -> Optional[str]:
    """Koordinata bo'yicha manzil matnini topish — sender o'z joylashuvini yuborganda."""
    data = await _request(
        {"geocode": f"{longitude},{latitude}", "kind": "house", "results": 1, "lang": "uz_UZ"}
    )
    if not data:
        return None
    results = _parse_members(data)
    return results[0].address if results else None
