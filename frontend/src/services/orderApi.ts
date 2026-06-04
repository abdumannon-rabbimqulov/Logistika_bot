import { apiRequest } from "../api";
import type { Order, OrderOfferPayload } from "../types/order";

export interface OrderOffer {
  id: number;
  order_id: number;
  driver_id: number;
  offered_price: number;
  currency: string;
  status: string;
  comment?: string | null;
  created_at: string;
}

export async function fetchOrders(params?: {
  status?: string;
  driver_id?: number;
  customer_id?: number;
}): Promise<Order[]> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.driver_id != null) q.set("driver_id", String(params.driver_id));
  if (params?.customer_id != null) q.set("customer_id", String(params.customer_id));
  const qs = q.toString();
  return apiRequest<Order[]>(`/orders${qs ? `?${qs}` : ""}`);
}

export async function fetchOrder(pk: number): Promise<Order> {
  return apiRequest<Order>(`/orders/${pk}`);
}

export async function createOrderOffer(
  orderId: number,
  data: OrderOfferPayload
): Promise<OrderOffer> {
  return apiRequest<OrderOffer>(`/orders/${orderId}/offers`, {
    method: "POST",
    body: JSON.stringify({
      offered_price: data.offered_price,
      currency: data.currency ?? "UZS",
      comment: data.comment ?? null,
      driver_latitude: data.driver_latitude ?? null,
      driver_longitude: data.driver_longitude ?? null,
    }),
  });
}

export async function patchOrderOffer(
  pk: number,
  data: { status?: string; counter_price?: number; counter_comment?: string }
): Promise<OrderOffer> {
  return apiRequest<OrderOffer>(`/orders/offers/${pk}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}
