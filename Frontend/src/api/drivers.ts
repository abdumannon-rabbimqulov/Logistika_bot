import { ApiError, api } from './client';
import type {
  BalanceTransaction,
  DriverCabinet,
  DriverCreateInput,
  DriverEarning,
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

/** "Daromad" ekrani uchun: har bir yakunlangan buyurtma, uning summasi va undan
 *  ushlab qolingan komissiya. Komissiya `balance_transactions` dan olinadi va
 *  serverda buyurtmaga bog'lanadi — bu yerda qo'shimcha so'rov kerak emas. */
export function listMyEarnings(
  params: { skip?: number; limit?: number } = {},
): Promise<DriverEarning[]> {
  return api.get<DriverEarning[]>('/drivers/me/earnings', {
    skip: params.skip,
    limit: params.limit,
  });
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
