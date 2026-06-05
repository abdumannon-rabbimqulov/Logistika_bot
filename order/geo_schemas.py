from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class GeoBounds(BaseModel):
    """Leaflet fitBounds: [[south, west], [north, east]]."""

    south: float
    west: float
    north: float
    east: float

    @classmethod
    def from_leaflet(cls, bounds: list | None) -> Optional["GeoBounds"]:
        if not bounds or len(bounds) != 2:
            return None
        sw, ne = bounds
        if len(sw) < 2 or len(ne) < 2:
            return None
        return cls(south=float(sw[0]), west=float(sw[1]), north=float(ne[0]), east=float(ne[1]))


class RegionListItem(BaseModel):
    id: int
    soato_id: Optional[int] = None
    name_uz: str
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    centroid_lat: Optional[float] = None
    centroid_lng: Optional[float] = None
    bounds: Optional[list] = None
    model_config = ConfigDict(from_attributes=True)


class RegionDetail(RegionListItem):
    geojson: Optional[dict[str, Any]] = None


class DistrictListItem(BaseModel):
    id: int
    region_id: int
    soato_id: Optional[int] = None
    name_uz: str
    name_ru: Optional[str] = None
    name_en: Optional[str] = None
    centroid_lat: Optional[float] = None
    centroid_lng: Optional[float] = None
    bounds: Optional[list] = None
    has_geometry: bool = False
    model_config = ConfigDict(from_attributes=True)


class DistrictDetail(DistrictListItem):
    geojson: Optional[dict[str, Any]] = None


class LocationConfirmPayload(BaseModel):
    region_id: int
    district_id: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: str = Field(..., min_length=1, max_length=300)
