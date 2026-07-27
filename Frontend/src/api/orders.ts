import { api } from './client';
import type {
  DispatchAttemptResponse,
  GeocodeSuggestion,
  Order,
  OrderCreateInput,
  OrderDetail,
  OrderListItem,
  OrderStatus,
  PriceEstimateLocation,
  PriceEstimateResponse,
  ReverseGeocodeResponse,
  WaypointProgressInput,
} from '../types/api';

export function createOrder(data: OrderCreateInput): Promise<OrderDetail> {
  return api.post<OrderDetail>('/orders', data);
}

export function listMyOrders(): Promise<OrderListItem[]> {
  return api.get<OrderListItem[]>('/orders');
}

export function getOrder(orderId: number): Promise<OrderDetail> {
  return api.get<OrderDetail>(`/orders/${orderId}`);
}

export function searchAddress(query: string): Promise<GeocodeSuggestion[]> {
  return api.get<GeocodeSuggestion[]>('/orders/geocode/search', { q: query });
}

export function reverseGeocode(latitude: number, longitude: number): Promise<ReverseGeocodeResponse> {
  return api.get<ReverseGeocodeResponse>('/orders/geocode/reverse', { latitude, longitude });
}

export function estimatePrice(
  origin: PriceEstimateLocation,
  destination: PriceEstimateLocation,
): Promise<PriceEstimateResponse> {
  return api.post<PriceEstimateResponse>('/orders/estimate-price', { origin, destination });
}

export function bumpPrice(orderId: number, price: number): Promise<OrderDetail> {
  return api.post<OrderDetail>(`/orders/${orderId}/price-bump`, { price });
}

// ── Haydovchi dispatch oqimi ────────────────────────────────────────────────────────
/** Haydovchining joriy faol taklifi (yo'q bo'lsa `null`). */
export function getActiveDispatch(): Promise<DispatchAttemptResponse | null> {
  return api.get<DispatchAttemptResponse | null>('/orders/dispatch/active');
}

/** Taklifni qabul qilish — buyurtma haydovchiga biriktiriladi, to'liq tafsilot qaytadi. */
export function acceptDispatch(attemptId: number): Promise<OrderDetail> {
  return api.post<OrderDetail>(`/orders/dispatch/${attemptId}/accept`);
}

/** Taklifni rad etish — navbat keyingi haydovchiga o'tadi (204). */
export function rejectDispatch(attemptId: number): Promise<void> {
  return api.post<void>(`/orders/dispatch/${attemptId}/reject`);
}

/** Buyurtma holatini qo'lda yangilash — FAQAT admin uchun.
 *  Haydovchi oqimni `updateWaypoint` orqali suradi (har qadam GPS bilan tekshiriladi). */
export function updateOrderStatus(orderId: number, status: OrderStatus): Promise<Order> {
  return api.patch<Order>(`/orders/${orderId}/status`, { status });
}

/** Marshrut nuqtasidagi qadamni belgilash ("Yetib keldim" / "Yukni ortdim" / "Topshirdim").
 *  Javobda yangilangan buyurtma to'liq qaytadi — qayta so'rov kerak emas. */
export function updateWaypoint(
  orderId: number,
  waypointId: number,
  data: WaypointProgressInput,
): Promise<OrderDetail> {
  return api.patch<OrderDetail>(`/orders/${orderId}/waypoints/${waypointId}`, data);
}
