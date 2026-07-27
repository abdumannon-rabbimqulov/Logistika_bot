import { getTelegramLocationOnce, isTelegramLocationSupported, TelegramLocationError } from './telegramLocation';

/** Bir martalik aniq GPS o'lchovi — buyurtma qadamini tasdiqlash uchun.
 *
 * Nega jonli kuzatuv (`useLiveLocation`) yetarli emas: u koordinatani 30 soniyada bir
 * marta yuboradi va Telegram WebApp fonga o'tganda OS uni butunlay to'xtatadi. Haydovchi
 * ilovani endi ochgan paytda serverdagi "oxirgi ma'lum nuqta" bir necha kilometr eskirgan
 * bo'lishi mumkin. Shuning uchun tugma bosilganda yangi o'lchov olinadi va u geofence
 * uchun asosiy manba bo'ladi (backend: services/geofence.py).
 *
 * Manba: Telegram ichida `LocationManager` (bor bo'lsa) ustuvor — oddiy
 * `navigator.geolocation` Telegram'ning ichki WebView'ida ko'pincha ishlamaydi
 * (`utils/telegramLocation.ts` izohiga qarang). Telegramdan tashqarida (dev/test
 * uchun oddiy brauzerda) brauzer geolocation'iga qaytiladi.
 */

export interface PositionSample {
  latitude: number;
  longitude: number;
  accuracy: number | null;
}

const TIMEOUT_MS = 15_000;

export class PositionError extends Error {
  /** `true` bo'lsa — UI "Sozlamalarni ochish" tugmasini ko'rsatishi kerak. */
  canOpenSettings: boolean;

  constructor(message: string, canOpenSettings = false) {
    super(message);
    this.canOpenSettings = canOpenSettings;
  }
}

function getBrowserPositionOnce(): Promise<PositionSample> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new PositionError("Qurilmangiz geolokatsiyani qo'llab-quvvatlamaydi"));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        resolve({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy ?? null,
        }),
      (err) => {
        // Xabar haydovchiga ko'rsatiladi, shuning uchun brauzerning inglizcha matni
        // o'rniga nima qilish kerakligi tushunarli qilib yoziladi.
        const message =
          err.code === err.PERMISSION_DENIED
            ? "Joylashuvga ruxsat berilmagan. Telefon sozlamalaridan ruxsat bering."
            : err.code === err.POSITION_UNAVAILABLE
              ? "Joylashuv aniqlanmadi. GPS yoqilganini tekshiring."
              : "Joylashuvni aniqlash uzoq davom etdi. Ochiq joyga chiqib qayta urining.";
        reject(new PositionError(message));
      },
      // `maximumAge: 10s` — `useLiveLocation` shu sahifada parallel ravishda
      // `watchPosition` orqali GPS'ni "issiq" tutib turadi (har ~5s yangilanadi),
      // shuning uchun so'nggi bir necha soniyalik nuqtani qayta ishlatish xavfsiz
      // va yangi to'liq GPS aniqlanishini (ba'zi qurilmalarda sekin/timeout
      // bo'lishi mumkin) kutishning hojati yo'q.
      { enableHighAccuracy: true, timeout: TIMEOUT_MS, maximumAge: 10_000 },
    );
  });
}

export async function getCurrentPositionOnce(): Promise<PositionSample> {
  if (isTelegramLocationSupported()) {
    try {
      return await getTelegramLocationOnce();
    } catch (err) {
      if (err instanceof TelegramLocationError) {
        throw new PositionError(err.message, err.canOpenSettings);
      }
      throw err;
    }
  }
  return getBrowserPositionOnce();
}
