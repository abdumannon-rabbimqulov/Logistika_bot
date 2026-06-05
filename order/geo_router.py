from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import get_db
from order import geo_crud, geo_schemas

router = APIRouter(prefix="/geo", tags=["Geo (Viloyat / Tuman)"])


@router.get("/regions", response_model=List[geo_schemas.RegionListItem], summary="Viloyatlar qidiruvi")
async def list_regions(
    q: Optional[str] = Query(None, description="Viloyat nomi bo'yicha qidiruv"),
    db: AsyncSession = Depends(get_db),
):
    return await geo_crud.search_regions(db, q=q)


@router.get("/regions/{pk}", response_model=geo_schemas.RegionDetail, summary="Viloyat + GeoJSON")
async def get_region(pk: int, db: AsyncSession = Depends(get_db)):
    region = await geo_crud.get_region(db, pk)
    if not region:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viloyat topilmadi")
    return region


@router.get(
    "/regions/{region_id}/districts",
    response_model=List[geo_schemas.DistrictListItem],
    summary="Tumanlar qidiruvi (viloyat bo'yicha)",
)
async def list_districts(
    region_id: int,
    q: Optional[str] = Query(None, description="Tuman nomi bo'yicha qidiruv"),
    db: AsyncSession = Depends(get_db),
):
    region = await geo_crud.get_region(db, region_id)
    if not region:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viloyat topilmadi")

    districts = await geo_crud.search_districts(db, region_id, q=q)
    return [
        geo_schemas.DistrictListItem(
            id=d.id,
            region_id=d.region_id,
            soato_id=d.soato_id,
            name_uz=d.name_uz,
            name_ru=d.name_ru,
            name_en=d.name_en,
            centroid_lat=float(d.centroid_lat) if d.centroid_lat is not None else None,
            centroid_lng=float(d.centroid_lng) if d.centroid_lng is not None else None,
            bounds=d.bounds,
            has_geometry=bool(d.geojson),
        )
        for d in districts
    ]


@router.get("/districts/{pk}", response_model=geo_schemas.DistrictDetail, summary="Tuman + GeoJSON")
async def get_district(pk: int, db: AsyncSession = Depends(get_db)):
    district = await geo_crud.get_district(db, pk)
    if not district:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tuman topilmadi")
    return geo_schemas.DistrictDetail(
        id=district.id,
        region_id=district.region_id,
        soato_id=district.soato_id,
        name_uz=district.name_uz,
        name_ru=district.name_ru,
        name_en=district.name_en,
        centroid_lat=float(district.centroid_lat) if district.centroid_lat is not None else None,
        centroid_lng=float(district.centroid_lng) if district.centroid_lng is not None else None,
        bounds=district.bounds,
        has_geometry=bool(district.geojson),
        geojson=district.geojson,
    )
