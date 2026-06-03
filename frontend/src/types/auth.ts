/** Backend UserRole bilan mos: admin | sender | driver | guest */

export type UserRole = "admin" | "sender" | "driver" | "guest";

export type AuthStatus = "active" | "need_driver_profile";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  role: UserRole;
  user_id: number;
  status?: AuthStatus | string;
  message?: string;
}

export interface LoginPayload {
  phone_number?: string;
  password?: string;
  init_data?: string;
}

export interface AuthSession {
  accessToken: string;
  refreshToken: string;
  role: UserRole;
  userId: number;
  status: AuthStatus;
  message?: string;
}

export interface LoginResult {
  session: AuthSession;
  redirectTo: string;
  message?: string;
}

export interface TruckType {
  id: number;
  name: string;
  max_weight: number;
  max_volume: number;
  length?: number | null;
  width?: number | null;
  height?: number | null;
  pallet_capacity?: number | null;
  image_url?: string | null;
  description?: string | null;
  is_active: boolean;
  created_at?: string;
}

export interface DriverProfileCreatePayload {
  truck_type_id: number;
  truck_number: string;
  truck_year?: number;
  current_city: string;
  current_region?: string;
  phone_number?: string;
}
