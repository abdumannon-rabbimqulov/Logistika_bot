import { getTelegramWebApp } from '../telegram';
import type { PositionSample } from './currentPosition';

/**
 * Telegram Mini App'ning o'z joylashuv menejeri (`LocationManager`, Bot API 8.0+).
 *
 * Nega kerak: bu ilova Telegram bot ichida WebApp sifatida ochiladi. Telegram'ning
 * ichki WebView'ida (ayniqsa Android/iOS mobil ilovada) oddiy `navigator.geolocation`
 * ko'pincha ishlamaydi — OS ruxsat oynasi umuman ko'rinmasdan doimiy
 * `PERMISSION_DENIED` qaytadi, chunki joylashuv ruxsati brauzer emas, Telegram
 * ilovasining o'ziga berilishi kerak. Shu sabab haydovchi tugmani bossa ham hech
 * narsa bo'lmagan yoki "ruxsat berilmagan" xatosi chiqavergan — bu holatda
 * `LocationManager` orqali so'ralgan ruxsat esa Telegram ilovasi darajasida ishlaydi.
 *
 * Eski Telegram klientlarida (yoki oddiy brauzerda, dev/test paytida) bu API mavjud
 * bo'lmasligi mumkin — shuning uchun barcha joyda mavjudligi tekshiriladi va
 * bo'lmasa chaqiruvchi brauzer geolocation'iga qaytishi kerak (`currentPosition.ts`,
 * `useLiveLocation.ts`).
 */

const MIN_BOT_API_VERSION = '8.0';

export function isTelegramLocationSupported(): boolean {
  const webApp = getTelegramWebApp();
  if (!webApp || !webApp.LocationManager) return false;
  try {
    return webApp.isVersionAtLeast(MIN_BOT_API_VERSION);
  } catch {
    // Juda eski klientlarda `isVersionAtLeast`ning o'zi bo'lmasligi mumkin.
    return false;
  }
}

let initPromise: Promise<void> | null = null;

/** `LocationManager.init()` bir marta chaqirilishi kerak — keyingi chaqiruvlar
 *  keshlangan promise'ni qaytaradi (qayta ishga tushirilmaydi). */
function ensureInited(): Promise<void> {
  if (initPromise) return initPromise;
  initPromise = new Promise((resolve) => {
    const manager = getTelegramWebApp()?.LocationManager;
    if (!manager) {
      resolve();
      return;
    }
    if (manager.isInited) {
      resolve();
      return;
    }
    manager.init(() => resolve());
  });
  return initPromise;
}

export class TelegramLocationError extends Error {
  /** `true` bo'lsa — foydalanuvchiga Telegram sozlamalarini ochish taklif qilinadi. */
  canOpenSettings: boolean;

  constructor(message: string, canOpenSettings = false) {
    super(message);
    this.canOpenSettings = canOpenSettings;
  }
}

/** Telegram sozlamalarida ilova uchun joylashuv ruxsatini ochadi (qo'lda rad etilgan holatda). */
export function openTelegramLocationSettings(): void {
  getTelegramWebApp()?.LocationManager?.openSettings();
}

export function getTelegramLocationOnce(): Promise<PositionSample> {
  return new Promise((resolve, reject) => {
    const webApp = getTelegramWebApp();
    const manager = webApp?.LocationManager;
    if (!manager) {
      reject(new TelegramLocationError('Telegram joylashuv menejeri mavjud emas'));
      return;
    }

    void ensureInited().then(() => {
      if (!manager.isLocationAvailable) {
        reject(
          new TelegramLocationError(
            "Qurilmada joylashuv xizmati o'chirilgan. Telefon sozlamalaridan GPS'ni yoqing.",
          ),
        );
        return;
      }

      manager.getLocation((data) => {
        if (!data) {
          // Ruxsat so'ralgan-u rad etilgan bo'lsa — sozlamalarni ochish tugmasi ko'rsatiladi.
          const canOpenSettings = manager.isAccessRequested && !manager.isAccessGranted;
          reject(
            new TelegramLocationError(
              canOpenSettings
                ? "Joylashuvga ruxsat berilmagan. Sozlamalardan Telegram uchun joylashuvni yoqing."
                : 'Joylashuv aniqlanmadi. Ochiq joyga chiqib qayta urinib ko\'ring.',
              canOpenSettings,
            ),
          );
          return;
        }
        resolve({
          latitude: data.latitude,
          longitude: data.longitude,
          accuracy: data.horizontal_accuracy ?? null,
        });
      });
    });
  });
}
