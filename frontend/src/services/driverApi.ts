import { apiRequest, API_BASE_URL } from "../api";
import type { DriverProfileCreatePayload, TruckType } from "../types/auth";
import type {
  AnnouncementCreatePayload,
  AnnouncementOffer,
  DriverAnnouncement,
  DriverProfile,
  DriverProfileUpdate,
  OfferUpdatePayload,
} from "../types/driver";

/** POST /drivers/truck-types — TruckTypeCreate (driver/schemas.py) */
export interface TruckTypePayload {
  name: string;
  max_weight: number;
  max_volume: number;
  length?: number | null;
  width?: number | null;
  height?: number | null;
  pallet_capacity?: number | null;
  image_url?: string | null;
  description?: string | null;
  is_active: boolean;
}

export const defaultTruckTypeForm = (): TruckTypePayload => ({
  name: "",
  max_weight: 0,
  max_volume: 0,
  length: null,
  width: null,
  height: null,
  pallet_capacity: null,
  image_url: null,
  description: null,
  is_active: true,
});

export function truckTypeToForm(t: TruckType): TruckTypePayload {
  return {
    name: t.name,
    max_weight: Number(t.max_weight),
    max_volume: Number(t.max_volume),
    length: t.length != null ? Number(t.length) : null,
    width: t.width != null ? Number(t.width) : null,
    height: t.height != null ? Number(t.height) : null,
    pallet_capacity: t.pallet_capacity ?? null,
    image_url: t.image_url ?? null,
    description: t.description ?? null,
    is_active: t.is_active,
  };
}

function optionalDecimal(value: number | null | undefined): number | null {
  if (value == null || Number.isNaN(value)) return null;
  return value > 0 ? value : null;
}

function optionalInt(value: number | null | undefined): number | null {
  if (value == null || Number.isNaN(value)) return null;
  const n = Math.trunc(value);
  return n > 0 ? n : null;
}

/** API ga yuborishdan oldin tozalash */
export function sanitizeTruckTypePayload(form: TruckTypePayload): TruckTypePayload {
  const description = form.description?.trim() || null;
  return {
    name: form.name.trim(),
    max_weight: Number(form.max_weight),
    max_volume: Number(form.max_volume),
    length: optionalDecimal(form.length ?? null),
    width: optionalDecimal(form.width ?? null),
    height: optionalDecimal(form.height ?? null),
    pallet_capacity: optionalInt(form.pallet_capacity ?? null),
    image_url: form.image_url?.trim() || null,
    description: description ? description.slice(0, 200) : null,
    is_active: form.is_active,
  };
}

export function validateTruckTypeForm(form: TruckTypePayload): string | null {
  if (!form.name.trim()) return "Nomi majburiy";
  if (form.name.trim().length > 50) return "Nomi 50 belgidan oshmasin";
  if (!form.max_weight || form.max_weight <= 0) return "Max og'irlik 0 dan katta bo'lishi kerak";
  if (!form.max_volume || form.max_volume <= 0) return "Max hajm 0 dan katta bo'lishi kerak";
  if (form.description && form.description.length > 200) return "Tavsif 200 belgidan oshmasin";
  if (form.image_url && form.image_url.length > 512) return "Rasm URL juda uzun";
  return null;
}

export async function fetchTruckTypes(): Promise<TruckType[]> {
  return apiRequest<TruckType[]>("/drivers/truck-types");
}

export async function fetchTruckType(pk: number): Promise<TruckType> {
  return apiRequest<TruckType>(`/drivers/truck-types/${pk}`);
}

export async function createTruckType(data: TruckTypePayload): Promise<TruckType> {
  return apiRequest<TruckType>("/drivers/truck-types", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTruckType(pk: number, data: Partial<TruckTypePayload>): Promise<TruckType> {
  return apiRequest<TruckType>(`/drivers/truck-types/${pk}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteTruckType(pk: number): Promise<void> {
  await apiRequest(`/drivers/truck-types/${pk}`, { method: "DELETE" });
}

export async function uploadTruckTypeImage(file: File): Promise<{ url: string; filename?: string }> {
  const form = new FormData();
  form.append("file", file);
  const token = localStorage.getItem("logistika_access_token");
  const base = API_BASE_URL.replace(/\/$/, "");
  const res = await fetch(`${base}/drivers/truck-types/image`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Rasm yuklanmadi");
  }
  return res.json();
}

export async function createDriverProfile(payload: DriverProfileCreatePayload): Promise<unknown> {
  return apiRequest("/drivers/profile", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchDriverMe(): Promise<DriverProfile> {
  return apiRequest<DriverProfile>("/drivers/me");
}

export async function updateDriverMe(data: DriverProfileUpdate): Promise<DriverProfile> {
  return apiRequest<DriverProfile>("/drivers/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function fetchAnnouncements(driverId?: number): Promise<DriverAnnouncement[]> {
  const q = driverId != null ? `?driver_id=${driverId}` : "";
  return apiRequest<DriverAnnouncement[]>(`/drivers/announcements${q}`);
}

export async function fetchAnnouncement(pk: number): Promise<DriverAnnouncement> {
  return apiRequest<DriverAnnouncement>(`/drivers/announcements/${pk}`);
}

export async function createAnnouncement(data: AnnouncementCreatePayload): Promise<DriverAnnouncement> {
  return apiRequest<DriverAnnouncement>("/drivers/announcements", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function fetchAnnouncementOffers(announcementId: number): Promise<AnnouncementOffer[]> {
  return apiRequest<AnnouncementOffer[]>(`/drivers/announcements/${announcementId}/offers`);
}

export async function updateOffer(pk: number, data: OfferUpdatePayload): Promise<AnnouncementOffer> {
  return apiRequest<AnnouncementOffer>(`/drivers/offers/${pk}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
