"""Yandex Geocoder API orqali manzil qidirish (forward) va aniqlash (reverse)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from config.config import API_YANDEX_KEY

logger = logging.getLogger(__name__)

GEOCODER_URL = "https://geocode-maps.yandex.ru/1.x/"
REQUEST_TIMEOUT = 5.0

# Qisqa muddatli natija keshi: `estimate-price` va shundan keyin darhol chaqiriladigan
# `create_order` bir xil manzil matni uchun BIR XIL koordinatani olishini kafolatlaydi —
# aks holda ikkalasi mustaqil geocode qilsa, Yandex boshqa "eng mos" natija qaytarishi
# mumkin va mijozga ko'rsatilgan narx bilan yakuniy buyurtma narxi farq qilib qolishi mumkin.
_SEARCH_CACHE_TTL_SEC = 300
_search_cache: dict[str, tuple[float, "list[GeocodeResult]"]] = {}


def _cache_get(key: str) -> Optional[list["GeocodeResult"]]:
    entry = _search_cache.get(key)
    if entry is None:
        return None
    cached_at, results = entry
    if time.monotonic() - cached_at > _SEARCH_CACHE_TTL_SEC:
        _search_cache.pop(key, None)
        return None
    return results


def _cache_set(key: str, results: list["GeocodeResult"]) -> None:
    # Xotira cheksiz o'smasligi uchun oddiy himoya — juda ko'p turli so'rov kelsa eskilari tozalanadi
    if len(_search_cache) > 2000:
        _search_cache.clear()
    _search_cache[key] = (time.monotonic(), results)


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
    normalized = query.strip().lower()
    cache_key = f"{normalized}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    data = await _request({"geocode": query.strip(), "results": limit, "lang": "uz_UZ"})
    if not data:
        return []
    results = _parse_members(data)
    if results:
        _cache_set(cache_key, results)
    return results


async def reverse_geocode(latitude: float, longitude: float) -> Optional[str]:
    """Koordinata bo'yicha manzil matnini topish — sender o'z joylashuvini yuborganda."""
    data = await _request(
        {"geocode": f"{longitude},{latitude}", "kind": "house", "results": 1, "lang": "uz_UZ"}
    )
    if not data:
        return None
    results = _parse_members(data)
    return results[0].address if results else None
