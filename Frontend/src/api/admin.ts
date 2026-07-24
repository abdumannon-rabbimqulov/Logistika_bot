import { api, getAccessToken } from './client';
import type {
  AdminDashboardStats,
  AdminUserList,
  AdminUserListItem,
  AdminUserUpdate,
  CommissionSettings,
  DriverLocationItem,
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
