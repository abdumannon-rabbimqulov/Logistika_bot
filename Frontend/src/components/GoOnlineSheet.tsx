import { useState } from 'react';
import { toLocalDateValue } from '../utils/pickupTime';
import { BottomSheetModal } from './BottomSheetModal';
import styles from './GoOnlineSheet.module.css';

const DATE_OPTIONS = [
  { days: 0, label: 'Hoziroq' },
  { days: 1, label: "1 kundan keyin" },
  { days: 2, label: "2 kundan keyin" },
  { days: 4, label: "4 kundan keyin" },
];

export interface GoOnlineResult {
  /** Ixtiyoriy — kiritilmasa yuborilmaydi (haydovchi joyi jonli GPS orqali aniqlanadi). */
  currentRegion?: string;
  availableFromDate: string | null; // ISO (YYYY-MM-DD) yoki hoziroq bo'lsa null
}

interface Props {
  onSubmit: (result: GoOnlineResult) => void;
  onClose: () => void;
  submitting: boolean;
}

/** N kundan keyingi sana (`YYYY-MM-DD`), "hoziroq" bo'lsa `null`.
 *
 *  Sana MAHALLIY mintaqada hisoblanadi. Ilgari bu yerda `toISOString().slice(0, 10)`
 *  turardi — u UTC sanani beradi va Toshkent vaqti bilan 00:00–05:00 orasida bir kun
 *  orqaga surilardi: haydovchi "1 kundan keyin" desa ham tizimga BUGUNGI sana yozilib,
 *  unga darhol hozirgi yuklar kela boshlardi (backend `available_from_date` filtri).
 */
function isoDateInDays(days: number): string | null {
  if (days === 0) return null;
  const d = new Date();
  d.setDate(d.getDate() + days);
  return toLocalDateValue(d);
}

// Liniyaga chiqishda haydovchi qachondan yuk qabul qilishini belgilaydi (hoziroq yoki
// kelajakdagi sana — masalan hozir boshqa buyurtmada bo'lsa ham). Joylashuv endi qo'lda
// kiritilmaydi: u jonli GPS orqali aniqlanadi (services/dispatch.py Tier A). Viloyat —
// ixtiyoriy qo'shimcha (GPS o'chiq bo'lganda Tier B matn moslashuvi uchun).
export function GoOnlineSheet({ onSubmit, onClose, submitting }: Props) {
  const [region, setRegion] = useState('');
  const [selectedDays, setSelectedDays] = useState(0);

  function handleSubmit() {
    onSubmit({
      currentRegion: region.trim() || undefined,
      availableFromDate: isoDateInDays(selectedDays),
    });
  }

  return (
    <BottomSheetModal title="Liniyaga chiqish" onClose={onClose}>
      <div className={styles.field}>
        <label className={styles.label}>Viloyat (ixtiyoriy)</label>
        <input className={styles.input} value={region} onChange={(e) => setRegion(e.target.value)} placeholder="Toshkent viloyati" />
        <div className={styles.hint}>
          Joylashuvingiz jonli GPS orqali avtomatik aniqlanadi. Viloyatni kiritsangiz, GPS
          o'chiq bo'lganda ham shu hudud bo'yicha yuk taklif qilinadi.
        </div>
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Qachondan yuk qabul qilasiz?</label>
        <div className={styles.dateGrid}>
          {DATE_OPTIONS.map((opt) => (
            <button
              key={opt.days}
              className={selectedDays === opt.days ? styles.dateBtnActive : styles.dateBtn}
              onClick={() => setSelectedDays(opt.days)}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className={styles.hint}>
          Hozir boshqa buyurtmada bo'lsangiz ham, kelajakdagi sana uchun oldindan liniyaga kirishingiz mumkin.
        </div>
      </div>

      <button className={styles.submitBtn} disabled={submitting} onClick={handleSubmit}>
        {submitting ? 'Yuborilmoqda...' : 'Liniyaga chiqish'}
      </button>
    </BottomSheetModal>
  );
}
