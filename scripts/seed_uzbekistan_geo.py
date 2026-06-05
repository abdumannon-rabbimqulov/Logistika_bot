#!/usr/bin/env python3
"""
O'zbekiston viloyat va tumanlarini bazaga bir marta yuklash.

Manbalar:
- Nomlar / SOATO (14 viloyat, 210 tuman):
  https://github.com/MIMAXUZ/uzbekistan-regions-data
- GeoJSON konturlar:
  https://github.com/dirixtt/GeoJSON-Uzbekistan

Ishlatish:
  python scripts/seed_uzbekistan_geo.py
  docker compose exec web python scripts/seed_uzbekistan_geo.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.geo_utils import (  # noqa: E402
    compute_bounds,
    compute_centroid,
    extract_geometry,
    names_match,
    normalize_name,
    slugify,
)

EXPECTED_REGIONS = 14
EXPECTED_DISTRICTS = 210

MIMAXUZ_REGIONS_URL = (
    "https://raw.githubusercontent.com/MIMAXUZ/uzbekistan-regions-data/master/JSON/regions.json"
)
MIMAXUZ_DISTRICTS_URL = (
    "https://raw.githubusercontent.com/MIMAXUZ/uzbekistan-regions-data/master/JSON/districts.json"
)
DIRIXTT_REGIONS_URL = (
    "https://raw.githubusercontent.com/dirixtt/GeoJSON-Uzbekistan/main/uzbekistan_regional.geojson"
)
DIRIXTT_DISTRICT_BASE = (
    "https://raw.githubusercontent.com/dirixtt/GeoJSON-Uzbekistan/main/regions_geoJSON/"
)

DATA_DIR = ROOT / "data" / "geo"

# MIMAXUZ soato_id -> dirixtt uzbekistan_regional.geojson properties.id
SOATO_TO_DIRIXTT_REGION_ID: dict[int, int] = {
    1703: 1,   # Andijon
    1706: 2,   # Buxoro
    1708: 3,   # Jizzax
    1710: 4,   # Qashqadaryo
    1712: 5,   # Navoiy
    1714: 6,   # Namangan
    1718: 7,   # Samarqand
    1722: 8,   # Surxondaryo
    1724: 9,   # Sirdaryo
    1726: 14,  # Toshkent shahri
    1727: 10,  # Toshkent viloyati
    1730: 11,  # Farg'ona
    1733: 12,  # Xorazm
    1735: 13,  # Qoraqalpog'iston
}

REGION_DISTRICT_FILE: dict[str, str | None] = {
    "andijon": "andijon_region_districts.geojson",
    "buxoro": "bukhara_region_districts.geojson",
    "fargona": "fargona_region_districts.geojson",
    "jizzax": "jizzakh_region_districts.geojson",
    "qashqadaryo": "qarshi_region_districts.geojson",
    "navoiy": "navoiy_region_districts.geojson",
    "namangan": None,
    "samarqand": "samarqand_region_districts.geojson",
    "sirdaryo": "sirdaryo_region_districts.geojson",
    "toshkent-shahri": "tashkent_districts.geojson",
    "toshkent-viloyati": "tashkent_region_districts.geojson",
    "surxondaryo": "surkhandarya_region_districts.geojson",
    "xorazm": "xorazm_region_districts.geojson",
    "qoraqalpogiston": "karakalpak.geojson",
}


def fetch_json(url: str) -> object:
    cache_name = url.split("/")[-1].replace("..", ".")
    cache_path = DATA_DIR / cache_name
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8-sig"))
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=120) as resp:
        raw = resp.read().decode("utf-8-sig")
    cache_path.write_text(raw, encoding="utf-8")
    return json.loads(raw)


def region_key_from_name(name_uz: str) -> str:
    lower = name_uz.lower()
    n = normalize_name(name_uz)
    if "toshkent" in n and ("shahri" in lower or "sh." in lower):
        return "toshkent-shahri"
    if "toshkent" in n:
        return "toshkent-viloyati"
    if "qoraqalpo" in n:
        return "qoraqalpogiston"
    if "farg" in n:
        return "fargona"
    if "qashqadar" in n:
        return "qashqadaryo"
    if "surxon" in n:
        return "surxondaryo"
    for key in ("andijon", "buxoro", "jizzax", "navoiy", "namangan", "samarqand", "sirdaryo", "xorazm"):
        if key in n:
            return key
    return slugify(name_uz)


def build_region_feature_map(features: list[dict]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for feature in features:
        props = feature.get("properties") or {}
        geo_id = props.get("id")
        if geo_id is not None:
            out[int(geo_id)] = feature
    return out


def resolve_region_feature(
    item: dict,
    feature_by_id: dict[int, dict],
    features: list[dict],
) -> dict | None:
    soato = item.get("soato_id")
    if soato and int(soato) in SOATO_TO_DIRIXTT_REGION_ID:
        geo_id = SOATO_TO_DIRIXTT_REGION_ID[int(soato)]
        if geo_id in feature_by_id:
            return feature_by_id[geo_id]

    name_uz = item.get("name_uz", "")
    for feature in features:
        props = feature.get("properties") or {}
        for cand in (props.get("ADM1_UZ"), props.get("ADM1_EN"), props.get("ADM1_RU")):
            if cand and names_match(name_uz, str(cand)):
                return feature
    return None


def district_name_from_feature(props: dict) -> str | None:
    return (
        props.get("ADM2_UZ")
        or props.get("ADM2_EN")
        or props.get("ADM2_RU")
        or props.get("name")
    )


def find_district_geometry(name_uz: str, geom_index: dict[str, dict]) -> dict | None:
    direct = geom_index.get(normalize_name(name_uz))
    if direct:
        return direct

    for key, payload in geom_index.items():
        if names_match(name_uz, key):
            return payload

    base = normalize_name(name_uz)
    for key, payload in geom_index.items():
        if base and (base in key or key in base):
            return payload

    return None


def build_district_geometry_index(region_key: str) -> dict[str, dict]:
    filename = REGION_DISTRICT_FILE.get(region_key)
    if not filename:
        return {}

    url = DIRIXTT_DISTRICT_BASE + filename
    try:
        collection = fetch_json(url)
    except Exception as exc:
        print(f"  ⚠ Tuman GeoJSON yuklanmadi ({filename}): {exc}")
        return {}

    index: dict[str, dict] = {}
    for feature in collection.get("features", []):
        props = feature.get("properties") or {}
        label = district_name_from_feature(props)
        if not label:
            continue
        geometry = extract_geometry(feature)
        if not geometry:
            continue
        payload = {
            "geojson": {"type": "Feature", "properties": props, "geometry": geometry},
            "bounds": compute_bounds(geometry),
            "name_en": props.get("ADM2_EN"),
        }
        for alias in (label, props.get("ADM2_EN"), props.get("ADM2_RU")):
            if alias:
                index[normalize_name(str(alias))] = payload
    return index


async def seed() -> None:
    from sqlalchemy import delete, func, select
    from sqlalchemy.orm import configure_mappers

    import ai.models  # noqa: F401
    import driver.models  # noqa: F401
    import users.models  # noqa: F401
    import order.models  # noqa: F401

    from config.config import async_session, engine, Base
    from order.models import District, Region

    configure_mappers()

    print("📥 Ma'lumotlar yuklanmoqda (MIMAXUZ + dirixtt)...")
    mimaxuz_regions: list[dict] = fetch_json(MIMAXUZ_REGIONS_URL)  # type: ignore[assignment]
    mimaxuz_districts: list[dict] = fetch_json(MIMAXUZ_DISTRICTS_URL)  # type: ignore[assignment]
    regional_geo = fetch_json(DIRIXTT_REGIONS_URL)  # type: ignore[assignment]
    region_features: list[dict] = regional_geo.get("features", [])
    feature_by_id = build_region_feature_map(region_features)

    if len(mimaxuz_regions) != EXPECTED_REGIONS:
        raise SystemExit(
            f"❌ MIMAXUZ viloyatlari: {len(mimaxuz_regions)} (kutilgan {EXPECTED_REGIONS})"
        )
    if len(mimaxuz_districts) != EXPECTED_DISTRICTS:
        raise SystemExit(
            f"❌ MIMAXUZ tumanlari: {len(mimaxuz_districts)} (kutilgan {EXPECTED_DISTRICTS})"
        )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        await db.execute(delete(District))
        await db.execute(delete(Region))
        await db.commit()

        region_id_map: dict[int, int] = {}
        regions_with_geo = 0

        print(f"🗺 {EXPECTED_REGIONS} ta viloyat yuklanmoqda...")
        for item in mimaxuz_regions:
            feature = resolve_region_feature(item, feature_by_id, region_features)
            geometry = extract_geometry(feature) if feature else None
            bounds = compute_bounds(geometry)
            centroid_lat, centroid_lng = compute_centroid(bounds)
            props = (feature or {}).get("properties") or {}

            if geometry:
                regions_with_geo += 1

            region = Region(
                soato_id=item.get("soato_id"),
                name_uz=item["name_uz"],
                name_oz=item.get("name_oz"),
                name_ru=item.get("name_ru"),
                name_en=props.get("ADM1_EN"),
                slug=region_key_from_name(item["name_uz"]),
                centroid_lat=centroid_lat,
                centroid_lng=centroid_lng,
                bounds=bounds,
                geojson=(
                    {"type": "Feature", "properties": props, "geometry": geometry}
                    if geometry
                    else None
                ),
            )
            db.add(region)
            await db.flush()
            region_id_map[item["id"]] = region.id

        await db.commit()
        print(f"✅ Viloyatlar: {EXPECTED_REGIONS} (GeoJSON: {regions_with_geo})")

        district_geom_cache: dict[str, dict[str, dict]] = {}
        matched_geom = 0
        skipped_region = 0

        print(f"📍 {EXPECTED_DISTRICTS} ta tuman yuklanmoqda...")
        for item in mimaxuz_districts:
            mimaxuz_region_id = item["region_id"]
            db_region_id = region_id_map.get(mimaxuz_region_id)
            if not db_region_id:
                skipped_region += 1
                continue

            result = await db.execute(select(Region).where(Region.id == db_region_id))
            region = result.scalar_one()
            region_key = region.slug or region_key_from_name(region.name_uz)

            if region_key not in district_geom_cache:
                district_geom_cache[region_key] = build_district_geometry_index(region_key)

            geom_data = find_district_geometry(
                item["name_uz"],
                district_geom_cache[region_key],
            )

            bounds = geom_data.get("bounds") if geom_data else None
            centroid_lat, centroid_lng = compute_centroid(bounds)
            if geom_data:
                matched_geom += 1

            district = District(
                region_id=db_region_id,
                soato_id=item.get("soato_id"),
                name_uz=item["name_uz"],
                name_oz=item.get("name_oz"),
                name_ru=item.get("name_ru"),
                name_en=geom_data.get("name_en") if geom_data else None,
                slug=slugify(item["name_uz"]),
                centroid_lat=centroid_lat,
                centroid_lng=centroid_lng,
                bounds=bounds,
                geojson=geom_data.get("geojson") if geom_data else None,
            )
            db.add(district)

        await db.commit()

        region_count = await db.scalar(select(func.count()).select_from(Region))
        district_count = await db.scalar(select(func.count()).select_from(District))

        print(f"✅ Tumanlar: {district_count} (GeoJSON: {matched_geom}, nom-only: {district_count - matched_geom})")
        if skipped_region:
            print(f"  ⚠ Region bog'lanmagan tumanlar: {skipped_region}")

        if region_count != EXPECTED_REGIONS or district_count != EXPECTED_DISTRICTS:
            raise SystemExit(
                f"❌ Bazada {region_count} viloyat, {district_count} tuman — "
                f"kutilgan {EXPECTED_REGIONS}/{EXPECTED_DISTRICTS}"
            )

        print("🎉 Seed muvaffaqiyatli yakunlandi.")


if __name__ == "__main__":
    asyncio.run(seed())
