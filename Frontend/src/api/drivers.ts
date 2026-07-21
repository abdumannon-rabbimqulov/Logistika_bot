import { ApiError, api } from './client';
import type { DriverCabinet, DriverCreateInput, DriverProfile, GoOnlineInput } from '../types/api';

export function createDriverProfile(data: DriverCreateInput): Promise<DriverProfile> {
  return api.post<DriverProfile>('/drivers/profile', data);
}

/** Profil hali yaratilmagan bo'lsa `null` qaytaradi (404'ni kutilgan holat sifatida ushlaydi). */
export async function getMyDriverCabinetOrNull(): Promise<DriverCabinet | null> {
  try {
    return await api.get<DriverCabinet>('/drivers/me');
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export function updateDriverAvailability(data: GoOnlineInput): Promise<DriverCabinet> {
  return api.patch<DriverCabinet>('/drivers/me', data);
}
