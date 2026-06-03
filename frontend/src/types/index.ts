export const UserRole = {
  ADMIN: "admin",
  DRIVER: "driver",
  CLIENT: "client",
  DISPATCHER: "dispatcher",
} as const;
export type UserRole = typeof UserRole[keyof typeof UserRole];

export interface User {
  id: number;
  username: string | null;
  full_name: string;
  email: string | null;
  phone_number: string | null;
  role: UserRole | null;
  language: string;
  is_active: boolean;
  is_banned: boolean;
  balance: number;
  created_at: string;
  updated_at: string;
}

export interface UserListResponse {
  total: number;
  items: User[];
}

export interface UserUpdateData {
  role?: UserRole | null;
  is_banned?: boolean;
  is_active?: boolean;
  language?: string;
  full_name?: string;
}

export const OrderStatus = {
  PENDING: "pending",
  ACCEPTED: "accepted",
  IN_PROGRESS: "in_progress",
  COMPLETED: "completed",
  CANCELLED: "cancelled",
} as const;
export type OrderStatus = typeof OrderStatus[keyof typeof OrderStatus];

export const WaypointType = {
  PICKUP: "pickup",
  DELIVERY: "delivery",
  TRANSIT: "transit",
} as const;
export type WaypointType = typeof WaypointType[keyof typeof WaypointType];

export const WaypointStatus = {
  PENDING: "pending",
  ARRIVED: "arrived",
  COMPLETED: "completed",
  SKIPPED: "skipped",
} as const;
export type WaypointStatus = typeof WaypointStatus[keyof typeof WaypointStatus];

export interface OrderWaypoint {
  id: number;
  order_id: number;
  sequence: number;
  waypoint_type: WaypointType;
  address: string;
  landmark: string | null;
  latitude: number | null;
  longitude: number | null;
  distance_from_prev_km: number | null;
  scheduled_arrival: string | null;
  scheduled_departure: string | null;
  actual_arrival: string | null;
  actual_departure: string | null;
  stop_duration_min: number | null;
  contact_name: string | null;
  contact_phone: string | null;
  note: string | null;
  status: WaypointStatus;
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: number;
  customer_id: number;
  driver_id: number | null;
  cargo_name: string;
  weight: number;
  volume: number | null;
  required_truck_type_id: number;
  price: number;
  currency: string;
  scheduled_start: string | null;
  scheduled_end: string | null;
  total_distance_km: number | null;
  status: OrderStatus;
  created_at: string;
  updated_at: string;
  waypoints: OrderWaypoint[];
}

export interface OrderUpdateData {
  status?: OrderStatus;
  cargo_name?: string;
  weight?: number;
  price?: number;
  currency?: string;
  description?: string;
}

export interface OrdersByDay {
  date: string;
  count: number;
}

export interface AdminDashboardStats {
  users_total: number;
  users_today: number;
  drivers_total: number;
  drivers_online: number;
  drivers_live_gps: number;
  orders_total: number;
  orders_today: number;
  orders_by_status: Record<OrderStatus | string, number>;
  offers_today: number;
  ai_requests_today: number;
  ai_input_tokens_today: number;
  ai_output_tokens_today: number;
  orders_last_7_days: OrdersByDay[];
}

export interface AICommand {
  id: number;
  user_id: number | null;
  message_id: number | null;
  command_type: string;
  raw_input: string | null;
  parameters: Record<string, any> | null;
  status: string;
  result: Record<string, any> | null;
  error_msg: string | null;
  created_at: string;
  executed_at: string | null;
}

export interface AICommandListResponse {
  total: number;
  items: AICommand[];
}

export interface DriverLocation {
  driver_id: number;
  user_id: number | null;
  full_name: string | null;
  truck_number: string | null;
  truck_type_id: number | null;
  lat: number;
  lon: number;
  ts: string;
  expires_at: string | null;
}
