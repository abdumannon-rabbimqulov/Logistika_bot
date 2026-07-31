// Backend sxemalariga mos TS interfeyslar (order/schemas.py, driver/schemas.py, users/schemas.py).
// Numeric (Decimal) maydonlar JSON orqali string yoki number bo'lib kelishi mumkin — shuning
// uchun hammasi `number` deb belgilangan va api/client.ts orqali normalizatsiya qilinadi.

export type UserRole = 'admin' | 'sender' | 'driver' | 'guest' | 'dispatcher' | 'manager';

export interface DriverCreateInput {
  truck_type_id: number;
  truck_number: string;
  truck_year?: number;
  /** Ixtiyoriy — ilovada so'ralmaydi, joylashuv jonli GPS orqali aniqlanadi. */
  current_city?: string;
  current_region?: string;
  phone_number?: string;
}

// POST /drivers/profile (yaratish) javobi — driver/schemas.py DriverResponse
export interface DriverProfile {
  id: number;
  user_id: number;
  truck_type_id: number;
  truck_number: string;
  truck_year: number | null;
  current_city: string | null;
  current_region: string | null;
  rating: number;
  total_trips: number;
  cancel_count: number;
  on_time_percent: number;
  is_available: boolean;
  is_blocked: boolean;
  block_reason: string | null;
  created_at: string;
  updated_at: string;
}

// GET/PATCH /drivers/me javobi — driver/schemas.py DriverProfileResponse (boshqacha shakl!)
export interface DriverCabinet {
  id: number;
  user_id: number;
  name: string;
  rating: number;
  balance: string;
  balance_amount: number;
  currency: string;
  user_status: 'LIVE' | 'OFFLINE';
  gps_status: 'ON' | 'OFF';
  phone_number: string | null;
  truck_type_id: number;
  truck_type_name: string | null;
  truck_number: string;
  truck_year: number | null;
  current_city: string | null;
  current_region: string | null;
  is_available: boolean;
  available_from_date: string | null;
  total_trips: number;
  on_time_percent: number;
  is_blocked: boolean;
}

export interface GoOnlineInput {
  is_available: boolean;
  current_city?: string;
  current_region?: string;
  available_from_date?: string | null;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  role: UserRole;
  user_id: number;
  status?: 'need_driver_profile';
  message?: string;
}

export interface UserProfile {
  id: number;
  username: string | null;
  full_name: string;
  email: string | null;
  phone_number: string | null;
  role: UserRole;
  language: string;
  is_active: boolean;
  is_banned: boolean;
  balance: number;
  created_at: string;
  updated_at: string;
}

export interface TruckType {
  id: number;
  name: string;
  max_weight: number;
  max_volume: number;
  length: number | null;
  width: number | null;
  height: number | null;
  pallet_capacity: number | null;
  base_price: number;
  price_per_km: number;
  min_price: number | null;
  image_url: string | null;
  description: string | null;
  is_active: boolean;
  created_at: string;
}

export type WaypointType = 'PICKUP' | 'DELIVERY' | 'TRANSIT';
export type WaypointStatus = 'PENDING' | 'ARRIVED' | 'COMPLETED' | 'SKIPPED';
export type OrderStatus = 'SCHEDULED' | 'PENDING' | 'ACCEPTED' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';

export interface OrderWaypoint {
  id: number;
  order_id: number;
  sequence: number;
  type: WaypointType;
  status: WaypointStatus;
  address: string | null;
  latitude: number | null;
  longitude: number | null;
  contact_name: string | null;
  contact_phone: string | null;
  created_at: string;
  /** Haydovchi "Yetib keldim" bosgan payt. */
  arrived_at: string | null;
  /** Nuqta yakunlangan (yuk ortilgan/topshirilgan) payt. */
  completed_at: string | null;
  /** Qadam tasdiqlanganda o'lchangan masofa (metr) — GPS isboti. */
  confirmed_distance_m: number | null;
  confirmed_accuracy_m: number | null;
  /** To'ldirilgan bo'lsa — qadam admin tomonidan qo'lda tasdiqlangan (geofence'siz). */
  override_by_user_id: number | null;
  override_reason: string | null;
}

/** PATCH /orders/{id}/waypoints/{wid} — nuqtadagi qadamni belgilash.
 *  Koordinata tugma bosilgan paytda olinadi (geofence uchun asosiy manba). */
export interface WaypointProgressInput {
  status: WaypointStatus;
  latitude?: number;
  longitude?: number;
  accuracy?: number;
  /** Faqat admin: GPS nosoz bo'lganda qadamni qo'lda tasdiqlash sababi. */
  override_reason?: string;
}

export interface OrderWaypointInput {
  sequence: number;
  type: WaypointType;
  address?: string;
  latitude?: number;
  longitude?: number;
  contact_name?: string;
  contact_phone?: string;
}

// GET /orders va GET /orders/available/list shu yengil sxemani qaytaradi — manzillar/waypoint YO'Q.
export interface OrderListItem {
  id: number;
  cargo_name: string;
  weight: number;
  price: number;
  currency: string;
  status: OrderStatus;
  pickup_at: string;
  driver_id: number | null;
  overload_warning: string | null;
  created_at: string;
  /** COMPLETED bo'lganda to'ldiriladi — daromad hisoboti shu sana bo'yicha guruhlanadi. */
  completed_at: string | null;
}

export interface Order {
  id: number;
  customer_id: number;
  driver_id: number | null;
  cargo_name: string;
  weight: number;
  volume: number | null;
  pickup_at: string;
  departure_at: string | null;
  required_truck_type_id: number;
  total_distance_km: number | null;
  price: number;
  original_price: number | null;
  currency: string;
  status: OrderStatus;
  dispatch_round: number;
  price_bump_requested_at: string | null;
  /** To'ldirilgan bo'lsa — haydovchi qidiruvi hali boshlanmagan va shu paytda
   *  boshlanadi (kelajakka rejalashtirilgan yuk). `null` — qidiruv ketmoqda. */
  dispatch_starts_at: string | null;
  overload_warning: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  waypoints: OrderWaypoint[];
}

/** Bir foydalanuvchi bilan bog'lanish uchun kerakli minimal ma'lumot (order/schemas.py TelegramContact). */
export interface TelegramContact {
  full_name: string;
  phone_number: string | null;
  username: string | null;
  /** Tayyor `https://t.me/<username>` havolasi — `username` bo'lmasa `null`. */
  telegram_url: string | null;
}

/** Haydovchi kontakti — mashina ma'lumoti bilan birga (order/schemas.py OrderDriverContact). */
export interface OrderDriverContact extends TelegramContact {
  truck_number: string;
  truck_type_name: string | null;
  rating: number;
}

/** GET /orders/{id}/driver-location va WS `location`/`update` hodisasi. */
export interface OrderDriverLocation {
  lat: number;
  lon: number;
  accuracy: number | null;
  ts: string;
}

export interface OrderDetail extends Order {
  origin: OrderWaypoint | null;
  destination: OrderWaypoint | null;
  current_waypoint: OrderWaypoint | null;
  /** Buyurtmaga haydovchi biriktirilgan bo'lsa to'ldiriladi — sender shu orqali
   *  haydovchi bilan bog'lanadi (tel/telegram). */
  driver_contact: OrderDriverContact | null;
  /** Haydovchi shu orqali buyurtmachi (sender) bilan bog'lanadi. */
  sender_contact: TelegramContact | null;
}

export interface OrderCreateInput {
  cargo_name: string;
  weight: number;
  volume?: number;
  pickup_at: string;
  required_truck_type_id: number;
  waypoints: OrderWaypointInput[];
}

// ── Avtomatik dispatch (haydovchiga navbat bilan yuboriladigan taklif) ──────────────
export type DispatchMatchType = 'gps' | 'region';
export type DispatchAttemptStatus = 'pending' | 'accepted' | 'rejected' | 'expired' | 'cancelled';

// GET /orders/dispatch/active javobidagi `order` xulosasi (order/schemas.py DispatchOrderSummary).
export interface DispatchOrderSummary {
  cargo_name: string;
  weight: number;
  price: number;
  currency: string;
  origin_address: string | null;
  destination_address: string | null;
  /** A→B marshrut uzunligi (buyurtmaning o'z masofasi) — `DispatchAttemptResponse.distance_km`
   *  bilan chalkashtirmaslik kerak: u haydovchidan A nuqtagacha bo'lgan masofa. */
  total_distance_km: number | null;
  origin_latitude: number | null;
  origin_longitude: number | null;
  destination_latitude: number | null;
  destination_longitude: number | null;
  /** OSRM marshrut chizig'i: [[latitude, longitude], ...] — xaritada chiziladi. */
  route_geometry: [number, number][];
}

// GET /orders/dispatch/active — null yoki joriy faol taklif (order/schemas.py DispatchAttemptResponse).
export interface DispatchAttemptResponse {
  id: number;
  order_id: number;
  driver_id: number;
  round_number: number;
  match_type: DispatchMatchType;
  /** Haydovchidan yuk ortish nuqtasigacha ("sizgacha") masofa — marshrut uzunligi EMAS. */
  distance_km: number | null;
  status: DispatchAttemptStatus;
  sent_at: string;
  expires_at: string;
  order: DispatchOrderSummary | null;
}

// ── Admin panel (Admin_panel/schemas.py) ────────────────────────────────────────────
export interface OrdersByDay {
  date: string; // YYYY-MM-DD
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
  /** Yakunlangan buyurtmalar bo'yicha umumiy aylanma (DB tomonda SUM bilan hisoblanadi). */
  revenue_total: number;
  orders_by_status: Record<string, number>;
  orders_last_7_days: OrdersByDay[];
}

export interface AdminUserListItem {
  id: number;
  username: string | null;
  full_name: string;
  email: string | null;
  phone_number: string | null;
  role: string | null;
  language: string;
  is_active: boolean;
  is_banned: boolean;
  balance: number;
  created_at: string;
  updated_at: string;
}

export interface AdminUserList {
  total: number;
  items: AdminUserListItem[];
}

export interface AdminUserUpdate {
  role?: UserRole;
  is_banned?: boolean;
  is_active?: boolean;
  language?: string;
  full_name?: string;
}

/** GET /system/drivers/monitor — xarita monitoringi (Admin_panel MonitorActiveOrder) */
export interface MonitorActiveOrder {
  id: number;
  cargo_name: string;
  weight: number;
  volume: number | null;
  price: number;
  currency: string;
  status: OrderStatus;
  origin_address: string | null;
  destination_address: string | null;
  current_waypoint_address: string | null;
  total_waypoints: number;
  completed_waypoints: number;
}

export interface DriverMonitorItem {
  driver_id: number;
  user_id: number;
  full_name: string | null;
  phone_number: string | null;
  truck_type_name: string | null;
  truck_number: string;
  is_available: boolean;
  is_blocked: boolean;
  block_reason: string | null;
  rating: number;
  total_trips: number;
  /** Hozir jonli GPS translyatsiya qilyapti (Redis'da yozuvi bor) */
  online: boolean;
  /** Faol (ACCEPTED/IN_PROGRESS) buyurtmasi bor — "yukli" */
  busy: boolean;
  latitude: number | null;
  longitude: number | null;
  location_source: 'live' | 'last_known' | null;
  location_at: string | null;
  active_order: MonitorActiveOrder | null;
}

export interface DriverLocationItem {
  driver_id: number;
  user_id: number | null;
  full_name: string | null;
  truck_number: string | null;
  truck_type_id: number | null;
  lat: number;
  lon: number;
  ts: string;
  expires_at: string | null;
  /** WS "update" xabarida keladi: haydovchi jonli translyatsiyani to'xtatdi (ro'yxatdan olib tashlanadi). */
  stopped?: boolean;
}

export interface CommissionSettings {
  commission_percent: number;
  updated_at: string;
}

/** GET /system/drivers — balans va blok holati bilan (Admin_panel AdminDriverListItem) */
export interface AdminDriverListItem {
  driver_id: number;
  user_id: number;
  full_name: string | null;
  phone_number: string | null;
  truck_number: string;
  truck_type_id: number;
  balance: number;
  is_blocked: boolean;
  block_reason: string | null;
  /** true — balans manfiy bo'lgani uchun tizim avtomatik bloklagan (admin qo'lda emas) */
  blocked_for_debt: boolean;
  is_available: boolean;
  verification_status: string;
  created_at: string;
}

export interface AdminDriverList {
  total: number;
  items: AdminDriverListItem[];
}

/** POST /orders/{id}/assign-driver javobidagi haydovchi bloki */
export interface AssignedDriverInfo {
  driver_id: number;
  user_id: number;
  full_name: string | null;
  phone_number: string | null;
  truck_number: string;
  truck_type_id: number;
  is_available: boolean;
  is_blocked: boolean;
  verification_status: string;
  rating: number;
  total_trips: number;
}

export interface OrderAssignDriverResponse {
  order: OrderDetail;
  driver: AssignedDriverInfo;
}

/** PATCH /system/orders/{id} — admin moderatsiyasi (Admin_panel AdminOrderUpdate) */
export interface AdminOrderUpdate {
  status?: OrderStatus;
  cargo_name?: string;
  weight?: number;
  price?: number;
  currency?: string;
}

/** "Daromad" ekranidagi bitta qator (GET /drivers/me/earnings).
 *
 *  `commission_amount` — platforma ushlab qolgan summa, MUSBAT son (bazada u
 *  manfiy saqlanadi, chunki balansdan yechiladi). `net_amount` — haydovchi
 *  qo'liga tushadigan sof summa. */
export interface DriverEarning {
  order_id: number;
  cargo_name: string;
  origin_address: string | null;
  destination_address: string | null;
  gross_amount: number;
  commission_amount: number;
  net_amount: number;
  currency: string;
  completed_at: string | null;
}

/** Balans harakati (GET /system/users/{id}/balance/transactions) */
export interface BalanceTransaction {
  id: number;
  user_id: number;
  type: string;
  amount: number;
  balance_after: number;
  order_id: number | null;
  created_by_admin_id: number | null;
  note: string | null;
  created_at: string;
}

export interface DriverUnblockPayload {
  /** Blokdan chiqarish bilan birga balansga qo'shiladigan summa (qarzni yopish uchun) */
  top_up_amount?: number;
  note?: string;
}

// POST/PATCH /drivers/truck-types uchun kirish (driver/schemas.py TruckTypeCreate/Update)
export interface TruckTypeInput {
  name: string;
  max_weight: number;
  max_volume: number;
  length?: number | null;
  width?: number | null;
  height?: number | null;
  pallet_capacity?: number | null;
  base_price: number;
  price_per_km: number;
  min_price?: number | null;
  image_url?: string | null;
  description?: string | null;
  is_active?: boolean;
}

export interface GeocodeSuggestion {
  address: string;
  latitude: number;
  longitude: number;
}

export interface ReverseGeocodeResponse {
  address: string | null;
  latitude: number;
  longitude: number;
}

export interface PriceEstimateLocation {
  address?: string;
  latitude?: number;
  longitude?: number;
}

/** Bitta "narxni oshirish" tugmasi — qiymatlarni backend beradi
 *  (services/pricing.py QUICK_PRICE_INCREMENTS), frontend hisoblamaydi. */
export interface QuickPriceOption {
  increment: number;
  price: number;
  currency: string;
}

/** GET /orders/{id}/price-options javobi. */
export interface OrderPriceOptionsResponse {
  order_id: number;
  currency: string;
  base_price: number;
  current_price: number;
  min_allowed_price: number;
  max_discount_percent: number;
  quick_price_options: QuickPriceOption[];
}

export interface PriceEstimateOption {
  truck_type_id: number;
  name: string;
  image_url: string | null;
  price: number;
  currency: string;
}

export interface PriceEstimateResponse {
  origin_address: string | null;
  origin_latitude: number;
  origin_longitude: number;
  destination_address: string | null;
  destination_latitude: number;
  destination_longitude: number;
  distance_km: number;
  duration_min: number;
  // OSRM marshrut chizig'i: [[latitude, longitude], ...] — xaritada ko'rsatiladi
  route_geometry: [number, number][];
  options: PriceEstimateOption[];
}
