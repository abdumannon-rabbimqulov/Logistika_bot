"""GeoJSON yordamchi funksiyalar (seed skript uchun)."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Iterable, Tuple


def normalize_name(value: str) -> str:
    """Viloyat/tuman nomlarini solishtirish uchun."""
    if not value:
        return ""
    text = value.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    for ch in ("ʻ", "ʼ", "`", "’", "‘", "″"):
        text = text.replace(ch, "'")
    text = text.replace("ғ", "g").replace("қ", "q").replace("ў", "o").replace("ҳ", "h")
    text = re.sub(r"\s+", " ", text)
    for suffix in (
        " tumani",
        " tuman",
        " shahri",
        " sh.",
        " sh",
        " viloyati",
        " viloyat",
        " respublikasi",
        " district",
        " city",
        " region",
    ):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    return text


def iter_coords(obj: Any) -> Iterable[Tuple[float, float]]:
    if isinstance(obj, (list, tuple)):
        if len(obj) >= 2 and isinstance(obj[0], (int, float)) and isinstance(obj[1], (int, float)):
            yield float(obj[1]), float(obj[0])
        else:
            for item in obj:
                yield from iter_coords(item)


def extract_geometry(feature: dict) -> dict | None:
    geom = feature.get("geometry")
    if not geom:
        return None
    if geom.get("type") == "GeometryCollection":
        parts = geom.get("geometries") or []
        if not parts:
            return None
        if len(parts) == 1:
            return parts[0]
        return geom
    return geom


def compute_bounds(geometry: dict | None) -> list | None:
    if not geometry:
        return None
    lats: list[float] = []
    lngs: list[float] = []
    for lat, lng in iter_coords(geometry.get("coordinates")):
        lats.append(lat)
        lngs.append(lng)
    if not lats:
        return None
    return [[min(lats), min(lngs)], [max(lats), max(lngs)]]


def compute_centroid(bounds: list | None) -> tuple[float | None, float | None]:
    if not bounds or len(bounds) != 2:
        return None, None
    sw, ne = bounds
    return (sw[0] + ne[0]) / 2, (sw[1] + ne[1]) / 2


def slugify(value: str) -> str:
    base = normalize_name(value)
    return re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "unknown"


def names_match(a: str, b: str) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na
