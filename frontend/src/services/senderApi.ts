import { senderHttp } from "./senderHttp";
import type { Order, OrderCreatePayload } from "../types/order";
import type { OrderOffer } from "./orderApi";

export async function createSenderOrder(data: OrderCreatePayload): Promise<Order> {
  const { data: result } = await senderHttp.post<Order>("/orders/", data);
  return result;
}

export async function fetchSenderOrders(): Promise<Order[]> {
  const { data } = await senderHttp.get<Order[]>("/orders/");
  return Array.isArray(data) ? data : [];
}

export async function fetchSenderOrder(pk: number): Promise<Order> {
  const { data } = await senderHttp.get<Order>(`/orders/${pk}`);
  return data;
}

export async function fetchSenderOrderOffers(orderId: number): Promise<OrderOffer[]> {
  const { data } = await senderHttp.get<OrderOffer[]>(`/orders/${orderId}/offers`);
  return Array.isArray(data) ? data : [];
}

export async function deleteSenderOrder(pk: number): Promise<void> {
  await senderHttp.delete(`/orders/${pk}`);
}

export async function patchSenderOrderOffer(
  pk: number,
  body: { status?: string; counter_price?: number; counter_comment?: string }
): Promise<OrderOffer> {
  const { data } = await senderHttp.patch<OrderOffer>(`/orders/offers/${pk}`, body);
  return data;
}
