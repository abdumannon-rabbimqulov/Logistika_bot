/** Bir martalik aniq GPS o'lchovi — buyurtma qadamini tasdiqlash uchun.
 *
 * Nega jonli kuzatuv (`useLiveLocation`) yetarli emas: u koordinatani 30 soniyada bir
 * marta yuboradi va Telegram WebApp fonga o'tganda OS uni butunlay to'xtatadi. Haydovchi
 * ilovani endi ochgan paytda serverdagi "oxirgi ma'lum nuqta" bir necha kilometr eskirgan
 * bo'lishi mumkin. Shuning uchun tugma bosilganda yangi o'lchov olinadi va u geofence
 * uchun asosiy manba bo'ladi (backend: services/geofence.py).
 */

export interface PositionSample {
  latitude: number;
  longitude: number;
  accuracy: number | null;
}

const TIMEOUT_MS = 12_000;

export class PositionError extends Error {}

export function getCurrentPositionOnce(): Promise<PositionSample> {
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
      // `maximumAge: 0` — keshdagi eski nuqta emas, aynan hozirgi o'lchov kerak.
      { enableHighAccuracy: true, timeout: TIMEOUT_MS, maximumAge: 0 },
    );
  });
}
