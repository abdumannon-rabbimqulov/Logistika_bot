// Menejer paneli — asosiy backendning `/manager` routeri (config/main.py orqali
// `/api/manager/...` bo'lib ochiladi), shuning uchun oddiy `api` wrapper'i ishlatiladi.
//
// Menejer admin EMAS: u buyurtmalarni yuritadi, lekin moliyaviy ma'lumotni ko'rmaydi.
// Backend narxni uch qatlamda kesadi (`/system` ga umuman kirita olmaydi, sxemalarda
// narx maydoni yo'q, `strip_finance_fields`). Frontendda ham narx ko'rsatilmasin.

import { api } from './client';
import type {
  AssignTruckResponse,
  AvailableTruck,
  ManagerOrderDetail,
  ManagerOrderListItem,
  OrderStatus,
} from '../types/api';

export interface ListManagerOrdersParams {
  status?: OrderStatus;
  /** Faqat haydovchi biriktirilmagan buyurtmalar — menejerning asosiy ish ro'yxati. */
  unassigned?: boolean;
  limit?: number;
  /** DIQQAT: bu router `skip` emas, `offset` ishlatadi (admin routeridan farqli). */
  offset?: number;
}

export function listManagerOrders(
  params: ListManagerOrdersParams = {},
): Promise<ManagerOrderListItem[]> {
  return api.get<ManagerOrderListItem[]>('/manager/orders', {
    status: params.status,
    unassigned: params.unassigned,
    limit: params.limit,
    offset: params.offset,
  });
}

export function getManagerOrder(orderId: number): Promise<ManagerOrderDetail> {
  return api.get<ManagerOrderDetail>(`/manager/orders/${orderId}`);
}

/** Holatlar o'rtasidagi ruxsat etilgan o'tishlar `services/order_flow.py` da —
 *  qoida buzilsa backend 400 qaytaradi (masalan yakunlangan buyurtmani qayta ochish). */
export function updateManagerOrderStatus(
  orderId: number,
  status: OrderStatus,
): Promise<ManagerOrderDetail> {
  return api.patch<ManagerOrderDetail>(`/manager/orders/${orderId}/status`, { status });
}

export interface AvailableTrucksParams {
  /** Faqat bo'sh, bloklanmagan va hujjati tasdiqlangan mashinalar (standart). */
  only_free?: boolean;
  /** Buyurtma talab qilgan turdan boshqasini ham ko'rsatish — favqulodda holat uchun. */
  any_truck_type?: boolean;
}

export function listAvailableTrucks(
  orderId: number,
  params: AvailableTrucksParams = {},
): Promise<AvailableTruck[]> {
  return api.get<AvailableTruck[]>(`/manager/orders/${orderId}/available-trucks`, {
    only_free: params.only_free,
    any_truck_type: params.any_truck_type,
  });
}

/** Biriktirish mantiqi serverda atomik (`services/dispatch.py assign_driver_manually`):
 *  ochiq takliflarni bekor qiladi va haydovchi/sender'ga xabar yuboradi. */
export function assignTruck(orderId: number, driverId: number): Promise<AssignTruckResponse> {
  return api.post<AssignTruckResponse>(`/manager/orders/${orderId}/assign-truck`, {
    driver_id: driverId,
  });
}
