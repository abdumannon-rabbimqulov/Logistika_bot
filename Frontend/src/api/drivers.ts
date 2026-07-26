import { ApiError, api } from './client';
import type {
  BalanceTransaction,
  DriverCabinet,
  DriverCreateInput,
  DriverProfile,
  GoOnlineInput,
} from '../types/api';

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

/** Profil sahifasidagi balans tarixi — komissiya yechilishi va to'ldirishlar. */
export function listMyBalanceTransactions(
  params: { skip?: number; limit?: number } = {},
): Promise<BalanceTransaction[]> {
  return api.get<BalanceTransaction[]>('/drivers/me/balance/transactions', {
    skip: params.skip,
    limit: params.limit,
  });
}
