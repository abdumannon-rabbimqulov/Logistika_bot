import { api, apiBaseUrl, getAccessToken } from './client';
import type {
  DispatchAttemptResponse,
  GeocodeSuggestion,
  Order,
  OrderCreateInput,
  OrderDetail,
  OrderDriverLocation,
  OrderListItem,
  OrderPriceOptionsResponse,
  OrderStatus,
  OrderUpdateInput,
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

/** Haydovchi uchun: hali haydovchisi topilmagan buyurtmalar. Faqat ko'rish uchun —
 *  qabul qilish dispatch taklifi orqali ketadi (`/orders/dispatch/...`), chunki
 *  navbat va 60 soniyalik taklif oynasi server tomonida boshqariladi. */
export function listAvailableOrders(truckTypeId?: number): Promise<OrderListItem[]> {
  return api.get<OrderListItem[]>('/orders/available/list', { truck_type_id: truckTypeId });
}

export function estimatePrice(
  origin: PriceEstimateLocation,
  destination: PriceEstimateLocation,
): Promise<PriceEstimateResponse> {
  return api.post<PriceEstimateResponse>('/orders/estimate-price', { origin, destination });
}

/** Buyurtmani tahrirlash (faqat egasi). Sxemada ATAYLAB faqat yuk ma'lumotlari bor —
 *  status/narx/haydovchi bu yerdan o'zgartirilmaydi (order/schemas.py OrderUpdate izohi).
 *  Server `extra="forbid"` qo'ygan, ya'ni ortiqcha maydon 422 qaytaradi. */
export function updateOrder(orderId: number, data: OrderUpdateInput): Promise<OrderDetail> {
  return api.patch<OrderDetail>(`/orders/${orderId}`, data);
}

/** Sender narxni qo'lda belgilaydi. Oshirish cheklanmagan; pasaytirish admin
 *  sozlamasidagi chegirma chegarasi bilan cheklangan — undan past narxda 400,
 *  buyurtma bu amalga yaroqsiz holatda bo'lsa 409 keladi. */
export function setCustomPrice(orderId: number, price: number): Promise<OrderDetail> {
  return api.patch<OrderDetail>(`/orders/${orderId}/price`, { price });
}

/** Narx oshirish variantlari (chegara + tayyor summalar) — botdagi tugmalar bilan bir xil. */
export function getPriceOptions(orderId: number): Promise<OrderPriceOptionsResponse> {
  return api.get<OrderPriceOptionsResponse>(`/orders/${orderId}/price-options`);
}

/** Narxni oshirib qidiruvni davom ettirish. Javob darhol qaytadi — qidiruvning
 *  o'zi RabbitMQ navbati orqali fon worker'ida ketadi (workers/dispatch_worker.py). */
export function bumpPrice(orderId: number, price: number): Promise<OrderDetail> {
  return api.post<OrderDetail>(`/orders/${orderId}/price-bump`, { price });
}

/** Buyurtmani bekor qilish (egasi). Haydovchi biriktirilgan bo'lsa ham ishlaydi,
 *  faqat IN_PROGRESS da backend 422 qaytaradi (yuk yo'lda — admin ishi).
 *  Javob 204: ochiq taklif yopiladi va taklif olgan haydovchi xabar oladi. */
export function cancelOrder(orderId: number, reason?: string): Promise<void> {
  const query = reason ? `?reason=${encodeURIComponent(reason)}` : '';
  return api.delete<void>(`/orders/${orderId}${query}`);
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

// ── Sender uchun jonli GPS kuzatuvi ─────────────────────────────────────────────────

/** Biriktirilgan haydovchining joriy lokatsiyasi (bir martalik so'rov — WS ulanmasdan
 *  oldingi boshlang'ich holat yoki WS ishlamasa zaxira sifatida). Haydovchi hali
 *  biriktirilmagan yoki jonli lokatsiya yo'q bo'lsa 404 (ApiError). */
export function getOrderDriverLocation(orderId: number): Promise<OrderDriverLocation> {
  return api.get<OrderDriverLocation>(`/orders/${orderId}/driver-location`);
}

/** WS /orders/{id}/ws/driver-location manzilini quradi — faqat shu buyurtmaning
 *  haydovchisi bo'yicha filtrlangan jonli oqim (order/router.py). */
export function orderDriverLocationWsUrl(orderId: number): string {
  const base = apiBaseUrl().replace(/\/$/, '');
  let httpBase: string;
  try {
    httpBase = new URL(base, window.location.origin).toString().replace(/\/$/, '');
  } catch {
    httpBase = `${window.location.origin}${base}`;
  }
  const wsBase = httpBase.replace(/^http/, 'ws');
  const token = getAccessToken() ?? '';
  return `${wsBase}/orders/${orderId}/ws/driver-location?token=${encodeURIComponent(token)}`;
}
