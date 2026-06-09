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
  counter_price?: number | null;
  counter_comment?: string | null;
  driver_latitude?: number | null;
  driver_longitude?: number | null;
  distance_to_pickup_km?: number | null;
  is_seen?: boolean;
  created_at: string;
  updated_at?: string;
  accepted_at?: string | null;
}

export interface FetchOrdersParams {
  status?: string;
  driver_id?: number;
  customer_id?: number;
  /** Haydovchi: true — faqat required_truck_type_id == driver.truck_type_id */
  filter_by_truck?: boolean;
}

export async function fetchOrders(params?: FetchOrdersParams): Promise<Order[]> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.driver_id != null) q.set("driver_id", String(params.driver_id));
  if (params?.customer_id != null) q.set("customer_id", String(params.customer_id));
  if (params?.filter_by_truck != null) {
    q.set("filter_by_truck", params.filter_by_truck ? "true" : "false");
  }
  const qs = q.toString();
  const path = qs ? `/orders/?${qs}` : "/orders/";

  try {
    const data = await apiRequest<Order[]>(path);
    if (!Array.isArray(data)) {
      console.warn("[fetchOrders] kutilgan massiv emas:", typeof data, data);
      return [];
    }
    return data;
  } catch (error) {
    console.error("[fetchOrders]", path, error);
    throw error;
  }
}

/** Haydovchi: pending buyurtmalar; filterByTruck — mashina turiga mos filtr. */
export async function fetchPendingOrders(filterByTruck = false): Promise<Order[]> {
  const path = `/orders/?status=PENDING&filter_by_truck=${filterByTruck}`;
  try {
    const data = await fetchOrders({
      status: "PENDING",
      filter_by_truck: filterByTruck,
    });
    const unassigned = data.filter((o) => o.driver_id == null);
    console.log("[fetchPendingOrders]", path, "→", unassigned.length, unassigned);
    return unassigned;
  } catch (error) {
    console.error("[fetchPendingOrders]", path, error);
    throw error;
  }
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

export async function acceptOrderDirectApi(orderId: number): Promise<Order> {
  return apiRequest<Order>(`/orders/${orderId}/accept`, {
    method: "POST",
  });
}
