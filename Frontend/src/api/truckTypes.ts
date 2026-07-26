import { api, apiBaseUrl, ApiError, getAccessToken } from './client';
import type { TruckType, TruckTypeInput } from '../types/api';

export function listTruckTypes(): Promise<TruckType[]> {
  return api.get<TruckType[]>('/drivers/truck-types', undefined, true);
}

export function getTruckType(id: number): Promise<TruckType> {
  return api.get<TruckType>(`/drivers/truck-types/${id}`, undefined, true);
}

export function createTruckType(data: TruckTypeInput): Promise<TruckType> {
  return api.post<TruckType>('/drivers/truck-types', data);
}

export function updateTruckType(id: number, data: Partial<TruckTypeInput>): Promise<TruckType> {
  return api.patch<TruckType>(`/drivers/truck-types/${id}`, data);
}

export function deleteTruckType(id: number): Promise<void> {
  return api.delete<void>(`/drivers/truck-types/${id}`);
}

/** Backend `/static/uploads/...` kabi nisbiy yo'l qaytaradi — uni ko'rsatish uchun
 *  API hostiga (BASE_URL dan `/api` olib tashlangan holda) bog'laymiz. */
export function staticFileUrl(path: string): string {
  if (/^https?:\/\//i.test(path)) return path;
  const origin = apiBaseUrl().replace(/\/api\/?$/, '');
  const base = origin || window.location.origin;
  return `${base}${path.startsWith('/') ? '' : '/'}${path}`;
}

/** POST /drivers/truck-types/image — rasm yuklaydi va statik URL qaytaradi.
 *  `api` wrapper JSON yuboradi, multipart uchun fetch to'g'ridan-to'g'ri ishlatiladi:
 *  Content-Type ni brauzer o'zi (boundary bilan) qo'yishi kerak. */
export async function uploadTruckTypeImage(file: File): Promise<string> {
  const body = new FormData();
  body.append('file', file);

  const headers = new Headers();
  const token = getAccessToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const res = await fetch(`${apiBaseUrl()}/drivers/truck-types/image`, {
    method: 'POST',
    headers,
    body,
  });

  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      // javob JSON emas
    }
    throw new ApiError(res.status, detail);
  }

  const data = (await res.json()) as { url: string };
  return data.url;
}
