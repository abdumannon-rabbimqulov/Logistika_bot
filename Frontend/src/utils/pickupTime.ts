/** Yuk tayyor bo'lish vaqtini tanlash uchun yordamchilar.
 *
 *  Diqqat qaratilgan joy — SOAT MINTAQASI. `<input type="datetime-local">` mahalliy
 *  vaqtni mintaqasiz matn ko'rinishida beradi ("2026-08-02T09:00"), backend esa
 *  mintaqali ISO 8601 kutadi (`order/schemas.py pickup_at`). Shuning uchun matn
 *  `new Date(...)` orqali mahalliy vaqt sifatida o'qiladi va `toISOString()` bilan
 *  UTC ga aylantiriladi. `toISOString()` ni to'g'ridan-to'g'ri input qiymatini
 *  yasashga ISHLATIB BO'LMAYDI — u UTC qaytaradi va foydalanuvchi tanlagan soat
 *  mintaqa farqiga siljib ketardi.
 */

/** Backend chegarasi bilan bir xil (`order/schemas.py MAX_PICKUP_DAYS_AHEAD`). */
export const MAX_PICKUP_DAYS_AHEAD = 90;

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

/** `Date` → `YYYY-MM-DD` MAHALLIY sana bo'yicha.
 *
 *  `toISOString().slice(0, 10)` ishlatib bo'lmaydi: u UTC sanani beradi va Toshkent
 *  (UTC+5) da tunda — 00:00 dan 05:00 gacha — bir kun ORQAGA suriladi. Haydovchi
 *  "1 kundan keyin" tugmasini bosganda tizimga bugungi sana yozilib qolardi va unga
 *  darhol hozirgi yuklar kela boshlardi.
 */
export function toLocalDateValue(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** `Date` → `<input type="datetime-local">` qiymati (mahalliy vaqt bo'yicha). */
export function toDateTimeLocalValue(date: Date): string {
  return `${toLocalDateValue(date)}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** `<input type="datetime-local">` qiymati → `Date` (yaroqsiz bo'lsa `null`). */
export function fromDateTimeLocalValue(value: string): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Tanlash mumkin bo'lgan eng erta payt — hozir (o'tmish tanlab bo'lmasin). */
export function minPickupValue(): string {
  return toDateTimeLocalValue(new Date());
}

/** Tanlash mumkin bo'lgan eng kech payt — backend chegarasi bilan bir xil. */
export function maxPickupValue(): string {
  const max = new Date();
  max.setDate(max.getDate() + MAX_PICKUP_DAYS_AHEAD);
  return toDateTimeLocalValue(max);
}

/** Tanlangan vaqtni tekshiradi; muammo bo'lsa o'zbekcha sabab, aks holda `null`.
 *
 *  Backenddagi `validate_pickup_time` bilan bir xil qoida — bu yerdagisi shunchaki
 *  tezroq javob berish uchun (so'rov yuborilmasdan). Yagona haqiqat manbai — server.
 */
export function validatePickupAt(date: Date | null): string | null {
  if (!date) return 'Yuk tayyor bo‘lish vaqtini tanlang';

  const now = new Date();
  // Bir daqiqalik imtiyoz — backenddagi `PICKUP_PAST_TOLERANCE` bilan bir xil.
  if (date.getTime() < now.getTime() - 60_000) {
    return 'Yuk tayyor bo‘lish vaqti o‘tmishda bo‘lishi mumkin emas';
  }

  const max = new Date();
  max.setDate(max.getDate() + MAX_PICKUP_DAYS_AHEAD);
  if (date.getTime() > max.getTime()) {
    return `Vaqtni ${MAX_PICKUP_DAYS_AHEAD} kundan uzoqqa belgilab bo‘lmaydi`;
  }
  return null;
}

/** Tanlangan vaqtni odam o'qiydigan ko'rinishda: "Bugun 14:30", "Ertaga 09:00",
 *  uzoqroq bo'lsa "2-avg, 09:00". */
export function describePickupAt(date: Date): string {
  const time = `${pad(date.getHours())}:${pad(date.getMinutes())}`;

  const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const dayDiff = Math.round((startOfDay(date) - startOfDay(new Date())) / 86_400_000);

  if (dayDiff === 0) return `Bugun ${time}`;
  if (dayDiff === 1) return `Ertaga ${time}`;
  if (dayDiff === 2) return `Indinga ${time}`;

  const day = date.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'short' });
  return `${day}, ${time}`;
}

export interface PickupPreset {
  label: string;
  /** Tugma bosilganda tanlanadigan payt. */
  build: () => Date;
}

/** Tez tanlash variantlari — foydalanuvchilarning aksariyati shu to'rttadan birini
 *  tanlaydi, kalendar esa faqat aniq sana kerak bo'lganda ochiladi. */
export const PICKUP_PRESETS: PickupPreset[] = [
  { label: 'Hozir', build: () => new Date() },
  {
    label: '2 soatdan keyin',
    build: () => new Date(Date.now() + 2 * 60 * 60 * 1000),
  },
  {
    label: 'Ertaga 09:00',
    build: () => {
      const d = new Date();
      d.setDate(d.getDate() + 1);
      d.setHours(9, 0, 0, 0);
      return d;
    },
  },
  {
    label: 'Indinga 09:00',
    build: () => {
      const d = new Date();
      d.setDate(d.getDate() + 2);
      d.setHours(9, 0, 0, 0);
      return d;
    },
  },
];
