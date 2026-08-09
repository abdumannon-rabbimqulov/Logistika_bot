/**
 * Yandex Maps'da A→B marshrutini ochadigan havola quruvchi.
 *
 * Havola formati (Yandex'ning rasmiy "build route" parametrlari):
 *
 *     https://yandex.com/maps/?rtext=<A>~<B>&rtt=auto
 *
 * `rtext` — tilda (`~`) bilan ajratilgan nuqtalar ro'yxati. Har bir nuqta ikki
 * xil bo'lishi mumkin:
 *   • koordinata — `41.311081,69.240562` (KENGLIK,UZUNLIK tartibida)
 *   • manzil matni — `Toshkent, Amir Temur ko'chasi 1`
 *
 * MOBIL QURILMADA: bu oddiy https havola, lekin iOS/Android'da Yandex Maps
 * ilovasi o'rnatilgan bo'lsa, universal link sifatida ilovaning o'zida ochiladi.
 * Ilova bo'lmasa brauzerda ochiladi. Shu sababli `yandexmaps://` sxemasi
 * ATAYLAB ishlatilmagan — u ilova yo'q qurilmada bo'sh sahifa qoldiradi.
 */

/** Marshrut nuqtasi — `OrderWaypoint` ning kerakli qismi bilan mos keladi.
 *
 *  Koordinata turi `number | string`: backend `latitude`/`longitude` ni Postgres
 *  `NUMERIC` dan oladi va Pydantic uni `Decimal` sifatida, JSON'da esa STRING
 *  ko'rinishida ("41.2845303") yuboradi. `types/api.ts` da tur `number` deb
 *  yozilgan — bu noaniqlik, lekin ish vaqtidagi haqiqat shu. Shuning uchun bu yerda
 *  ikkalasi ham qabul qilinadi (aks holda havola koordinata o'rniga manzil matniga
 *  tushib qolardi — brauzerda aynan shu xato ushlandi). */
export interface YandexRoutePoint {
  address?: string | null;
  latitude?: number | string | null;
  longitude?: number | string | null;
}

/** `rtt` — marshrut turi. Logistika uchun doim `auto`, qolganlari to'liqlik uchun. */
export type YandexRoutingMode = 'auto' | 'masstransit' | 'pedestrian' | 'bicycle';

const YANDEX_MAPS_BASE = 'https://yandex.com/maps/';

/** Koordinatani songa keltiradi; yaroqsiz bo'lsa `null`.
 *
 *  Bo'sh satr ATAYLAB rad etiladi: `Number('')` → 0, ya'ni tekshiruvsiz u
 *  Gvineya ko'rfazidagi (0, 0) nuqtaga aylanib qolardi. */
function toCoordinate(value: number | string | null | undefined): number | null {
  if (value === null || value === undefined || value === '') return null;
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
}

/**
 * Bitta nuqtani `rtext` bo'lagiga aylantiradi.
 *
 * Koordinata ustunroq: manzil matni Yandex qidiruvidan o'tadi va noto'g'ri joyni
 * topishi mumkin (bir xil nomli ko'chalar, imlo farqlari), koordinata esa aniq
 * nuqtani ko'rsatadi. Koordinata bo'lmasa — manzil matniga qaytamiz.
 *
 * `null` qaytsa — nuqta yaroqsiz (na koordinata, na manzil bor).
 */
function toRtextPart(point: YandexRoutePoint): string | null {
  const lat = toCoordinate(point.latitude);
  const lon = toCoordinate(point.longitude);
  if (lat !== null && lon !== null) {
    // Raqam, nuqta, vergul va minus URL'da xavfsiz belgilar — kodlash shart emas
    // (aksincha, vergulni %2C ga aylantirish havolani o'qishga qiyin qiladi).
    return `${lat},${lon}`;
  }

  const address = point.address?.trim();
  if (!address) return null;

  // Manzilda bo'shliq, kirill, apostrof bo'lishi mumkin — kodlanadi.
  // `encodeURIComponent` `~` ni kodlamaydi, shuning uchun ajratuvchi buzilmaydi:
  // manzil ichidagi tilda bo'lsa ham u xuddi shu ko'rinishda qoladi. Aynan shu
  // sababli quyida bo'laklar `~` bilan QO'LDA birlashtiriladi va butun `rtext`
  // qayta kodlanmaydi.
  return encodeURIComponent(address);
}

/**
 * "Yandex Xaritada ochish" tugmasi uchun havola.
 *
 * Ikkala nuqtadan biri yaroqsiz bo'lsa `null` qaytaradi — chaqiruvchi shu holatda
 * tugmani ko'rsatmasligi kerak (ishlamaydigan tugmadan ko'ra yo'q tugma yaxshi).
 *
 * @example
 * buildYandexRouteUrl(
 *   { latitude: 41.311081, longitude: 69.240562 },
 *   { address: "Samarqand, Registon" },
 * )
 * // → https://yandex.com/maps/?rtext=41.311081,69.240562~Samarqand%2C%20Registon&rtt=auto
 */
export function buildYandexRouteUrl(
  start: YandexRoutePoint | null | undefined,
  end: YandexRoutePoint | null | undefined,
  mode: YandexRoutingMode = 'auto',
): string | null {
  if (!start || !end) return null;

  const startPart = toRtextPart(start);
  const endPart = toRtextPart(end);
  if (!startPart || !endPart) return null;

  // Ikkala nuqta bir xil bo'lsa marshrutning ma'nosi yo'q — Yandex bo'sh natija
  // ko'rsatadi. Bunday holatda shunchaki o'sha nuqtani xaritada ochamiz.
  if (startPart === endPart) return buildYandexPointUrl(end);

  return `${YANDEX_MAPS_BASE}?rtext=${startPart}~${endPart}&rtt=${mode}`;
}

/**
 * Bitta nuqtani Yandex Maps'da ochadigan havola (marshrutsiz).
 *
 * Marshrut qurishning iloji bo'lmaganda ishlatiladi — masalan boshlanish nuqtasi
 * noma'lum (foydalanuvchi joylashuvga ruxsat bermagan) yoki u tugash nuqtasi bilan
 * bir xil. Foydalanuvchi manzilni xaritada ko'radi va navigatsiyani Yandex ichida
 * o'zi boshlaydi.
 *
 * `pt` parametri — Yandex'da UZUNLIK,KENGLIK tartibida (`rtext` dagidan TESKARI).
 * Bu Yandex API'sining o'ziga xosligi; almashtirib yuborilsa nuqta boshqa
 * mamlakatga tushib qoladi.
 */
export function buildYandexPointUrl(
  point: YandexRoutePoint | null | undefined,
  zoom = 16,
): string | null {
  if (!point) return null;
  const lat = toCoordinate(point.latitude);
  const lon = toCoordinate(point.longitude);

  if (lat !== null && lon !== null) {
    return `${YANDEX_MAPS_BASE}?pt=${lon},${lat}&z=${zoom}&l=map`;
  }

  // Koordinata yo'q — manzil matni bo'yicha qidiruv.
  const address = point.address?.trim();
  return address ? `${YANDEX_MAPS_BASE}?text=${encodeURIComponent(address)}` : null;
}
