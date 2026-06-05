import { apiRequest } from "../api";
import type { District, DistrictDetail, Region, RegionDetail } from "../types/geo";

export async function fetchRegions(q?: string): Promise<Region[]> {
  const qs = q?.trim() ? `?q=${encodeURIComponent(q.trim())}` : "";
  const data = await apiRequest<Region[]>(`/geo/regions${qs}`);
  return Array.isArray(data) ? data : [];
}

export async function fetchRegion(pk: number): Promise<RegionDetail> {
  return apiRequest<RegionDetail>(`/geo/regions/${pk}`);
}

export async function fetchDistricts(regionId: number, q?: string): Promise<District[]> {
  const params = new URLSearchParams();
  if (q?.trim()) params.set("q", q.trim());
  const qs = params.toString();
  const path = qs
    ? `/geo/regions/${regionId}/districts?${qs}`
    : `/geo/regions/${regionId}/districts`;
  const data = await apiRequest<District[]>(path);
  return Array.isArray(data) ? data : [];
}

export async function fetchDistrict(pk: number): Promise<DistrictDetail> {
  return apiRequest<DistrictDetail>(`/geo/districts/${pk}`);
}
