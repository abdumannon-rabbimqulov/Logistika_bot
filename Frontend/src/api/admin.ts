import { api, getAccessToken } from './client';
import type {
  AdminDashboardStats,
  AdminDriverList,
  AdminDriverListItem,
  AdminUserList,
  AdminUserListItem,
  AdminUserUpdate,
  BalanceTransaction,
  CommissionSettings,
  DriverLocationItem,
  DriverUnblockPayload,
  Order,
} from '../types/api';

// ── Dashboard ────────────────────────────────────────────────────────────────
export function getDashboardStats(): Promise<AdminDashboardStats> {
  return api.get<AdminDashboardStats>('/system/dashboard/stats');
}

// ── Foydalanuvchilar ───────────────────────────────────────────────────────────
export interface ListUsersParams {
  role?: string;
  is_banned?: boolean;
  is_active?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}

export function listUsers(params: ListUsersParams = {}): Promise<AdminUserList> {
  return api.get<AdminUserList>('/system/users', {
    role: params.role,
    is_banned: params.is_banned,
    is_active: params.is_active,
    search: params.search,
    skip: params.skip,
    limit: params.limit,
  });
}

export function updateUser(userId: number, data: AdminUserUpdate): Promise<AdminUserListItem> {
  return api.patch<AdminUserListItem>(`/system/users/${userId}`, data);
}

// ── Buyurtmalar (admin moderatsiya) ─────────────────────────────────────────────
export interface ListAdminOrdersParams {
  status?: string;
  driver_id?: number;
  customer_id?: number;
  skip?: number;
  limit?: number;
}

export function listAdminOrders(params: ListAdminOrdersParams = {}): Promise<Order[]> {
  return api.get<Order[]>('/system/orders', {
    status: params.status,
    driver_id: params.driver_id,
    customer_id: params.customer_id,
    skip: params.skip,
    limit: params.limit,
  });
}

// ── Haydovchilar: balans va bloklar ─────────────────────────────────────────────
export interface ListDriversParams {
  /** true — faqat bloklanganlar (qarz uchun avtomatik + qo'lda bloklanganlar) */
  is_blocked?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
}

export function listDrivers(params: ListDriversParams = {}): Promise<AdminDriverList> {
  return api.get<AdminDriverList>('/system/drivers', {
    is_blocked: params.is_blocked,
    search: params.search,
    skip: params.skip,
    limit: params.limit,
  });
}

/** Blokdan chiqarish. `top_up_amount` berilsa avval balans to'ldiriladi (qarz yopiladi). */
export function unblockDriver(
  driverId: number,
  payload: DriverUnblockPayload = {},
): Promise<AdminDriverListItem> {
  return api.post<AdminDriverListItem>(`/system/drivers/${driverId}/unblock`, payload);
}

export function blockDriver(driverId: number, reason: string): Promise<AdminDriverListItem> {
  return api.post<AdminDriverListItem>(`/system/drivers/${driverId}/block`, { reason });
}

// ── Balans (qo'lda to'ldirish / tuzatish) ────────────────────────────────────────
export function adjustUserBalance(
  userId: number,
  amount: number,
  note?: string,
): Promise<BalanceTransaction> {
  return api.post<BalanceTransaction>(`/system/users/${userId}/balance/adjust`, { amount, note });
}

export function listBalanceTransactions(
  userId: number,
  params: { skip?: number; limit?: number } = {},
): Promise<BalanceTransaction[]> {
  return api.get<BalanceTransaction[]>(`/system/users/${userId}/balance/transactions`, {
    skip: params.skip,
    limit: params.limit,
  });
}

// ── Haydovchi jonli lokatsiyalari ────────────────────────────────────────────────
export function listDriverLocations(): Promise<DriverLocationItem[]> {
  return api.get<DriverLocationItem[]>('/system/drivers/locations');
}

/** WS /system/drivers/locations/stream — real-time lokatsiya oqimi manzilini quradi.
 *  BASE_URL nisbiy (/api) yoki absolyut (http://host/api) bo'lishi mumkin — ikkalasini ham qamraydi. */
export function driverLocationsWsUrl(): string {
  const base = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api').replace(/\/$/, '');
  let httpBase: string;
  try {
    httpBase = new URL(base, window.location.origin).toString().replace(/\/$/, '');
  } catch {
    httpBase = `${window.location.origin}${base}`;
  }
  const wsBase = httpBase.replace(/^http/, 'ws');
  const token = getAccessToken() ?? '';
  return `${wsBase}/system/drivers/locations/stream?token=${encodeURIComponent(token)}`;
}

// ── Komissiya sozlamasi ─────────────────────────────────────────────────────────
export function getCommissionSettings(): Promise<CommissionSettings> {
  return api.get<CommissionSettings>('/system/settings/commission');
}

export function updateCommission(commissionPercent: number): Promise<CommissionSettings> {
  return api.patch<CommissionSettings>('/system/settings/commission', {
    commission_percent: commissionPercent,
  });
}
