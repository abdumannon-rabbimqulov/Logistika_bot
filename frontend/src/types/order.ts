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

export interface OrderWaypoint {
  id: number;
  order_id: number;
  sequence: number;
  waypoint_type: string;
  address: string;
  landmark?: string | null;
  status: string;
}

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
