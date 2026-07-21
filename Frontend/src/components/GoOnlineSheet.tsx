import { useEffect, useState } from 'react';
import { reverseGeocode } from '../api/orders';
import { useGeolocation } from '../hooks/useGeolocation';
import { BottomSheetModal } from './BottomSheetModal';
import styles from './GoOnlineSheet.module.css';

const DATE_OPTIONS = [
  { days: 0, label: 'Hoziroq' },
  { days: 1, label: "1 kundan keyin" },
  { days: 2, label: "2 kundan keyin" },
  { days: 4, label: "4 kundan keyin" },
];

export interface GoOnlineResult {
  currentCity: string;
  currentRegion?: string;
  availableFromDate: string | null; // ISO (YYYY-MM-DD) yoki hoziroq bo'lsa null
}

interface Props {
  onSubmit: (result: GoOnlineResult) => void;
  onClose: () => void;
  submitting: boolean;
}

function isoDateInDays(days: number): string | null {
  if (days === 0) return null;
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

// Liniyaga chiqishda haydovchi qayerdaligini (dispatch moslashtiruvchisi shundan
// foydalanadi — services/dispatch.py Tier B) va qachondan yuk qabul qilishini
// (hoziroq yoki kelajakdagi sana — masalan hozir boshqa buyurtmada bo'lsa ham) belgilaydi.
export function GoOnlineSheet({ onSubmit, onClose, submitting }: Props) {
  const geolocation = useGeolocation();
  const [city, setCity] = useState('');
  const [region, setRegion] = useState('');
  const [selectedDays, setSelectedDays] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [detecting, setDetecting] = useState(false);

  useEffect(() => {
    if (!geolocation.coords || city) return;
    setDetecting(true);
    reverseGeocode(geolocation.coords.latitude, geolocation.coords.longitude)
      .then((res) => {
        if (res.address) setCity(res.address);
      })
      .catch(() => {
        // aniqlanmasa — qo'lda kiritadi
      })
      .finally(() => setDetecting(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geolocation.coords]);

  function handleSubmit() {
    if (!city.trim()) {
      setError('Shahringizni kiriting');
      return;
    }
    setError(null);
    onSubmit({
      currentCity: city.trim(),
      currentRegion: region.trim() || undefined,
      availableFromDate: isoDateInDays(selectedDays),
    });
  }

  return (
    <BottomSheetModal title="Liniyaga chiqish" onClose={onClose}>
      <div className={styles.field}>
        <label className={styles.label}>Hozir qayerdasiz? (shahar)</label>
        <input className={styles.input} value={city} onChange={(e) => setCity(e.target.value)} placeholder="Toshkent" />
        {detecting && <div className={styles.hint}>Joylashuv aniqlanmoqda...</div>}
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Viloyat (ixtiyoriy)</label>
        <input className={styles.input} value={region} onChange={(e) => setRegion(e.target.value)} placeholder="Toshkent viloyati" />
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

      {error && <div className={styles.error}>{error}</div>}

      <button className={styles.submitBtn} disabled={submitting} onClick={handleSubmit}>
        {submitting ? 'Yuborilmoqda...' : 'Liniyaga chiqish'}
      </button>
    </BottomSheetModal>
  );
}
