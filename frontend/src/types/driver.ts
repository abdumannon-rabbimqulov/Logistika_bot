export type UserStatus = "LIVE" | "OFFLINE";
export type GpsStatus = "ON" | "OFF";

/** GET /drivers/me, /drivers/profile */
export interface DriverProfile {
  id: number;
  user_id: number;
  name: string;
  rating: number;
  balance: string;
  balance_amount: number;
  currency: string;
  user_status: UserStatus;
  gps_status: GpsStatus;
  phone_number?: string | null;
  truck_type_id: number;
  truck_type_name?: string | null;
  truck_number: string;
  truck_year?: number | null;
  current_city?: string | null;
  current_region?: string | null;
  is_available: boolean;
  total_trips: number;
  on_time_percent: number;
  is_blocked: boolean;
}

export interface DriverProfileUpdate {
  truck_type_id?: number;
  truck_number?: string;
  truck_year?: number;
  current_city?: string;
  current_region?: string;
  is_available?: boolean;
}

export type AnnouncementWaypointType = "origin" | "destination" | "transit";
export type AnnouncementStatus = "active" | "filled" | "expired" | "cancelled";
export type OfferStatus =
  | "pending"
  | "seen"
  | "accepted"
  | "rejected"
  | "cancelled"
  | "expired"
  | "outbid";

export interface AnnouncementWaypoint {
  id?: number;
  sequence: number;
  waypoint_type: AnnouncementWaypointType;
  city: string;
  region?: string | null;
  address?: string | null;
  note?: string | null;
}

export interface DriverAnnouncement {
  id: number;
  driver_id: number;
  price: number;
  currency: string;
  available_weight?: number | null;
  available_volume?: number | null;
  departure_date: string;
  arrival_date?: string | null;
  description?: string | null;
  status: AnnouncementStatus;
  total_distance_km?: number | null;
  created_at: string;
  waypoints: AnnouncementWaypoint[];
}

export interface AnnouncementCreatePayload {
  driver_id: number;
  price: number;
  currency?: string;
  available_weight?: number | null;
  available_volume?: number | null;
  departure_date: string;
  arrival_date?: string | null;
  description?: string | null;
  waypoints: Omit<AnnouncementWaypoint, "id">[];
}

export interface AnnouncementOffer {
  id: number;
  announcement_id: number;
  customer_id: number;
  cargo_name: string;
  cargo_description?: string | null;
  cargo_weight?: number | null;
  cargo_volume?: number | null;
  pickup_city?: string | null;
  delivery_city?: string | null;
  offered_price: number;
  currency: string;
  comment?: string | null;
  counter_price?: number | null;
  counter_comment?: string | null;
  status: OfferStatus;
  created_at: string;
}

export interface OfferUpdatePayload {
  status?: OfferStatus;
  counter_price?: number;
  counter_comment?: string;
}
