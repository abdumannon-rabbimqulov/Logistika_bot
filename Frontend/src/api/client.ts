// Fetch wrapper: Bearer token qo'shadi, 401 kelsa /auth/refresh bilan bitta marta avtomatik
// urinib qayta so'raydi. Refresh ham muvaffaqiyatsiz bo'lsa, tokenlar tozalanadi va
// `setUnauthorizedHandler` orqali ro'yxatdan o'tgan handler (AuthProvider) xabardor qilinadi —
// u qayta Telegram init_data bilan login qiladi.

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api').replace(/\/$/, '');

// Support — yagona ALOHIDA mikroservis (o'z image'i, o'z bazasi, port 8010). U asosiy
// app'ning `/api` prefiksi ostida EMAS, yo'llari to'g'ridan-to'g'ri `/support/...` bo'ladi.
// Standart holatda bo'sh satr: brauzer `/support/tickets` ni frontend bilan bir originda
// so'raydi va uni proxy backendga uzatadi (dev — vite.config.ts, prod — nginx.conf).
// Shu sababli CORS ham, alohida domen ham kerak emas. Xizmatga to'g'ridan-to'g'ri
// (proxy'siz) murojaat qilish kerak bo'lsagina `VITE_SUPPORT_BASE_URL` beriladi.
const SUPPORT_BASE_URL = (import.meta.env.VITE_SUPPORT_BASE_URL ?? '').replace(/\/$/, '');

const ACCESS_KEY = 'yuk_access_token';
const REFRESH_KEY = 'yuk_refresh_token';

/** API bazasi — `api` wrapper'idan tashqarida (masalan multipart yuklashda) kerak bo'ladi. */
export function apiBaseUrl(): string {
  return BASE_URL;
}

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

/** Bitta pydantic validatsiya xatosi (FastAPI 422 javobidagi element). */
interface ValidationIssue {
  loc?: unknown[];
  msg?: string;
}

/** Buzilgan biznes qoidasi: kod, o'zbekcha sabab va aniq raqamlar.
 *  Backend `services/problems.py Violation` bilan bir xil (kontekst maydonlari
 *  `code`/`message` yoniga yoyilgan holda keladi: `distance_m`, `allowed_radius_m`,
 *  `expected_waypoint_id` va h.k.). */
export interface ApiProblem {
  code: string;
  message: string;
  [key: string]: unknown;
}

/** `detail` obyektidan sabablar ro'yxatini ajratadi (bo'lmasa — bo'sh massiv). */
function extractProblems(detail: unknown): ApiProblem[] {
  if (typeof detail !== 'object' || detail === null) return [];
  const errors = (detail as { errors?: unknown }).errors;
  if (!Array.isArray(errors)) return [];
  return errors.filter(
    (item): item is ApiProblem =>
      typeof item === 'object' &&
      item !== null &&
      typeof (item as ApiProblem).code === 'string' &&
      typeof (item as ApiProblem).message === 'string',
  );
}

/** Backend xato javobidan o'qiladigan matnni ajratib oladi.
 *
 *  Backend uch xil shaklda javob berishi mumkin va ilgari faqat BIRINCHISI
 *  o'qilardi — qolganlarida foydalanuvchi "So'rov xato qaytardi (422)" degan
 *  ma'nosiz xabarni ko'rardi:
 *
 *  1. `{"detail": "matn"}` — `HTTPException(...)` (geofence, order_flow va h.k.);
 *  2. `{"detail": [{"loc": ["body","status"], "msg": "..."}]}` — FastAPI'ning
 *     so'rov validatsiyasi (422). `String()` bu massivni "[object Object]" ga
 *     aylantirardi — aynan shu "tushunarsiz 422" ning sababi edi;
 *  3. `{"message": "...", "details": {"errors": [{"field","message"}]}}` —
 *     `middlewares/error_handler.py` dagi standart shakl (DB/JWT xatolari);
 *  4. `{"detail": {"message": "...", "errors": [{"code","message",...}]}}` —
 *     biznes qoidalari buzilganda BARCHA sabablar birdan (`services/problems.py`),
 *     masalan `PATCH /orders/{id}/waypoints/{wp}`.
 */
function extractErrorMessage(status: number, body: unknown): string {
  const fallback = `So'rov xato qaytardi (${status})`;
  if (typeof body !== 'object' || body === null) return fallback;

  const { detail, message, details } = body as {
    detail?: unknown;
    message?: unknown;
    details?: { errors?: { field?: string; message?: string }[] };
  };

  if (typeof detail === 'string' && detail.trim()) return detail;

  const problems = extractProblems(detail);
  if (problems.length) return problems.map((p) => p.message).join(' ');

  if (typeof detail === 'object' && detail !== null) {
    const detailMessage = (detail as { message?: unknown }).message;
    if (typeof detailMessage === 'string' && detailMessage.trim()) return detailMessage;
  }

  if (Array.isArray(detail)) {
    const parts = (detail as ValidationIssue[])
      .map((issue) => {
        // `loc` odatda ["body", "maydon"] — foydalanuvchiga maydon nomi bilan ko'rsatamiz.
        const field = Array.isArray(issue.loc) ? issue.loc.slice(1).join('.') : '';
        const text = issue.msg ?? '';
        if (!text) return '';
        return field ? `${field}: ${text}` : text;
      })
      .filter(Boolean);
    if (parts.length) return parts.join('; ');
  }

  const fieldErrors = details?.errors;
  if (Array.isArray(fieldErrors) && fieldErrors.length) {
    const parts = fieldErrors
      .map((e) => (e.field ? `${e.field}: ${e.message ?? ''}` : e.message ?? ''))
      .filter(Boolean);
    if (parts.length) return parts.join('; ');
  }

  if (typeof message === 'string' && message.trim()) return message;

  return fallback;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  /** Buzilgan qoidalar ro'yxati (backend bergan bo'lsa). `message` — ularning
   *  birlashmasi; bu maydon esa sabablarni alohida ko'rsatish yoki `code` bo'yicha
   *  amal taklif qilish uchun (masalan `WRONG_WAYPOINT` da kerakli nuqtaga o'tish). */
  problems: ApiProblem[];

  constructor(status: number, detail: unknown) {
    super(extractErrorMessage(status, detail));
    this.status = status;
    this.detail = detail;
    this.problems = extractProblems(
      typeof detail === 'object' && detail !== null
        ? (detail as { detail?: unknown }).detail ?? detail
        : detail,
    );
  }
}

type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  unauthorizedHandler = handler;
}

let refreshInFlight: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;
    try {
      const res = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) return false;
      const body = (await res.json()) as { access_token: string; refresh_token: string };
      setTokens(body.access_token, body.refresh_token);
      return true;
    } catch {
      return false;
    }
  })();

  const result = await refreshInFlight;
  refreshInFlight = null;
  return result;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
  skipAuth?: boolean;
  /** Boshqa xizmat bazasi (masalan support). Berilmasa asosiy `BASE_URL` ishlatiladi. */
  baseUrl?: string;
}

function buildUrl(path: string, query?: RequestOptions['query'], baseUrl?: string): string {
  // Ikkinchi argument (base) BASE_URL nisbiy ("/api", nginx proxy uchun) bo'lganda kerak —
  // `new URL()` bazasiz nisbiy manzilni sinxron ravishda tashlaydi (hech qanday tarmoq
  // so'rovi yuborilmasdan), BASE_URL absolyut bo'lganda esa bu argument shunchaki e'tiborga
  // olinmaydi (URL spetsifikatsiyasi bo'yicha), shuning uchun ikkala holatda ham xavfsiz.
  const url = new URL(`${baseUrl ?? BASE_URL}${path}`, window.location.origin);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function request<T>(path: string, options: RequestOptions = {}, allowRetry = true): Promise<T> {
  const headers = new Headers({ 'Content-Type': 'application/json' });
  const token = getAccessToken();
  if (token && !options.skipAuth) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(buildUrl(path, options.query, options.baseUrl), {
    method: options.method ?? 'GET',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (res.status === 401 && allowRetry && !options.skipAuth && getRefreshToken()) {
    const refreshed = await tryRefresh();
    if (refreshed) return request<T>(path, options, false);
    clearTokens();
    unauthorizedHandler?.();
  }

  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      // javob JSON emas — detail null qoladi
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string, query?: RequestOptions['query'], skipAuth?: boolean) =>
    request<T>(path, { method: 'GET', query, skipAuth }),
  post: <T>(path: string, body?: unknown, skipAuth?: boolean) =>
    request<T>(path, { method: 'POST', body, skipAuth }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

/** Support mikroservisiga so'rovlar — `api` bilan bir xil wrapper, faqat boshqa baza.
 *
 *  Token AYNAN o'sha access token: support uni asosiy app bilan umumiy `SECRET_KEY`
 *  orqali lokal tekshiradi (`support_service/auth.py`), ya'ni xizmatlararo hech qanday
 *  chaqiruv yo'q. Shuning uchun 401 kelganda ham refresh asosiy app'ning
 *  `/auth/refresh` iga boradi — token beruvchi faqat o'sha. */
export const supportApi = {
  get: <T>(path: string, query?: RequestOptions['query']) =>
    request<T>(path, { method: 'GET', query, baseUrl: SUPPORT_BASE_URL }),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body, baseUrl: SUPPORT_BASE_URL }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body, baseUrl: SUPPORT_BASE_URL }),
};
