export type OrderStatus =
  | "PENDING"
  | "ACCEPTED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED";

export type OfferStatus =
  | "pending"
  | "seen"
  | "accepted"
  | "rejected"
  | "cancelled"
  | "expired"
  | "outbid";

export type WaypointType = "pickup" | "delivery" | "transit";

export interface OrderWaypoint {
  id: number;
  order_id: number;
  sequence: number;
  waypoint_type: WaypointType | string;
  address: string;
  landmark?: string | null;
  note?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  status: string;
}

export interface OrderWaypointCreatePayload {
  sequence: number;
  waypoint_type: WaypointType;
  address: string;
  note?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface OrderCreatePayload {
  cargo_name: string;
  weight: number;
  volume?: number | null;
  required_truck_type_id: number;
  price: number;
  currency?: string;
  waypoints: OrderWaypointCreatePayload[];
}

export type SenderOrderTab = "PENDING" | "ACTIVE" | "COMPLETED";

export const SENDER_ACTIVE_STATUSES: OrderStatus[] = ["ACCEPTED", "IN_PROGRESS"];

export interface Order {
  id: number;
  customer_id: number;
  driver_id?: number | null;
  cargo_name: string;
  weight: number;
  volume?: number | null;
  required_truck_type_id: number;
  price: number;
  currency: string;
  status: OrderStatus;
  total_distance_km?: number | null;
  created_at: string;
  waypoints: OrderWaypoint[];
}

export interface OrderOfferPayload {
  offered_price: number;
  currency?: string;
  comment?: string | null;
  driver_latitude?: number | null;
  driver_longitude?: number | null;
}
