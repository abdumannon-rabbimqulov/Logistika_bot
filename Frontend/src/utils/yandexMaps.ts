// Yandex Maps JS API (v2.1) skriptini bir marta yuklaydi va promise orqali qaytaradi —
// bir nechta xarita komponenti bir vaqtda render bo'lsa ham skript faqat bir marta qo'shiladi.

declare global {
  interface Window {
    ymaps?: YMaps;
  }
}

// To'liq TypeScript turlari yo'q (rasmiy @types paketi yo'q) — shu sabab kerakli
// metodlar minimal shaklda e'lon qilingan, qolgani `any` orqali ishlaydi.
export interface YMaps {
  ready(callback: () => void): void;
  Map: new (element: HTMLElement, state: Record<string, unknown>, options?: Record<string, unknown>) => YMap;
  Placemark: new (
    geometry: [number, number],
    properties?: Record<string, unknown>,
    options?: Record<string, unknown>,
  ) => unknown;
  GeoObjectCollection: new () => unknown;
  util: { bounds: { fromPoints(points: [number, number][]): [[number, number], [number, number]] } };
}

export interface YMap {
  geoObjects: { add(obj: unknown): unknown; remove(obj: unknown): unknown; removeAll(): unknown };
  container: { fitToViewport(): void };
  setBounds(bounds: [[number, number], [number, number]], options?: Record<string, unknown>): unknown;
  setCenter(center: [number, number], zoom?: number, options?: Record<string, unknown>): unknown;
  destroy(): void;
}

// O'zbekiston chegaralarini qamrab oluvchi to'rtburchak — xarita shu hududdan
// tashqariga siljib ketmasligi (restrictMapArea) uchun ishlatiladi.
export const UZBEKISTAN_BOUNDS: [[number, number], [number, number]] = [
  [37.0, 55.9],
  [45.6, 73.3],
];

export const UZBEKISTAN_CENTER: [number, number] = [41.377491, 64.585262];
export const UZBEKISTAN_DEFAULT_ZOOM = 6;

let loadPromise: Promise<YMaps> | null = null;

export function loadYandexMaps(): Promise<YMaps> {
  if (loadPromise) return loadPromise;

  loadPromise = new Promise((resolve, reject) => {
    if (window.ymaps) {
      window.ymaps.ready(() => resolve(window.ymaps!));
      return;
    }
    const apiKey = import.meta.env.VITE_YANDEX_MAPS_API_KEY;
    const script = document.createElement('script');
    script.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`;
    script.async = true;
    script.onload = () => window.ymaps!.ready(() => resolve(window.ymaps!));
    script.onerror = () => {
      loadPromise = null;
      reject(new Error("Yandex Maps skriptini yuklab bo'lmadi"));
    };
    document.head.appendChild(script);
  });

  return loadPromise;
}
