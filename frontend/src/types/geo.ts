/** Geo API va OrderMapSearch uchun TypeScript turlari */

export type LeafletBounds = [[number, number], [number, number]];

export type MapSearchStep = 1 | 2 | 3;

/** Viloyat (qisqa ro'yxat elementi) */
export interface Region {
  id: number;
  soato_id?: number | null;
  name_uz: string;
  name_ru?: string | null;
  name_en?: string | null;
  centroid_lat?: number | null;
  centroid_lng?: number | null;
  bounds?: LeafletBounds | null;
}

/** Viloyat tafsiloti (GeoJSON bilan) */
export interface RegionDetail extends Region {
  geojson?: GeoJSON.Feature | GeoJSON.FeatureCollection | GeoJSON.Geometry | null;
}

/** Tuman (qisqa ro'yxat elementi) */
export interface District {
  id: number;
  region_id: number;
  soato_id?: number | null;
  name_uz: string;
  name_ru?: string | null;
  name_en?: string | null;
  centroid_lat?: number | null;
  centroid_lng?: number | null;
  bounds?: LeafletBounds | null;
  has_geometry?: boolean;
}

/** Tuman tafsiloti (GeoJSON bilan) */
export interface DistrictDetail extends District {
  geojson?: GeoJSON.Feature | GeoJSON.FeatureCollection | GeoJSON.Geometry | null;
}

/** @deprecated Region nomi — Region ishlating */
export type RegionItem = Region;

/** @deprecated District nomi — District ishlating */
export type DistrictItem = District;

export interface MapSearchLocation {
  regionId: number;
  regionName: string;
  districtId: number;
  districtName: string;
  latitude?: number | null;
  longitude?: number | null;
  address: string;
}

export interface OrderMapSearchProps {
  pointLabel?: string;
  latitude?: number | null;
  longitude?: number | null;
  onLocationPick: (location: MapSearchLocation) => void;
  index?: number;
}

export type MapFlyMode = "idle" | "fitRegion" | "flyDistrict" | "flyPoint";

export type MapFlyCenter = [number, number];

export interface MapFlyCommand {
  mode: MapFlyMode;
  bounds?: LeafletBounds | null;
  center?: MapFlyCenter | null;
  zoom?: number;
}

export function boundsToLeaflet(bounds: LeafletBounds | null | undefined): LeafletBounds | null {
  if (!bounds || bounds.length !== 2) return null;
  return bounds;
}
