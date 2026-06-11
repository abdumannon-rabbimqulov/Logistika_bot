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


def levenshtein_distance(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def phonetic_normalize(value: str) -> str:
    text = normalize_name(value)
    # Remove punctuation & apostrophes
    text = re.sub(r"[^a-z0-9\s]", "", text)
    # Common sound equivalents
    text = text.replace("dzh", "j").replace("zh", "j")
    text = text.replace("kh", "h").replace("gh", "g").replace("sh", "s").replace("ch", "c")
    text = text.replace("q", "k").replace("x", "h").replace("w", "v")
    # Vocal normalization
    text = text.replace("o", "a").replace("u", "a").replace("e", "a").replace("i", "a")
    return text.replace(" ", "")


def names_match(a: str, b: str) -> bool:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    
    p_a = phonetic_normalize(a)
    p_b = phonetic_normalize(b)
    if p_a == p_b or p_a in p_b or p_b in p_a:
        return True
        
    dist = levenshtein_distance(p_a, p_b)
    max_len = max(len(p_a), len(p_b))
    if max_len > 0 and (dist / max_len) <= 0.30:
        return True
        
    return False
