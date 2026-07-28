/** Telefon maydonlari uchun namuna (placeholder) matni.
 *
 * ATAYLAB `+998` siz: backend (`utils/validation.py` → `normalize_phone_number`) raqamni
 * `phonenumbers` (Google libphonenumber) bilan "UZ" regioni bo'yicha tahlil qiladi, ya'ni
 * 9 xonali lokal raqam yetarli — "901234567", "90 123 45 67" va "+998901234567" bir xil
 * natijaga (E.164: +998901234567) keladi.
 *
 * Ilgari bu yerda "+998 XX XXX XX XX" turardi va davlat kodini yozish majburiy degan
 * taassurot berardi.
 */
export const PHONE_PLACEHOLDER = '90 123 45 67';
