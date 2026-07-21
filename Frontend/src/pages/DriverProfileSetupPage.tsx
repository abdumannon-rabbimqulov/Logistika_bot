import { useEffect, useState } from 'react';
import { ApiError } from '../api/client';
import { createDriverProfile } from '../api/drivers';
import { listTruckTypes } from '../api/truckTypes';
import type { TruckType } from '../types/api';
import styles from './DriverProfileSetupPage.module.css';

interface Props {
  onCreated: () => void;
}

// Backend `POST /drivers/profile` (driver/schemas.py DriverCreate) talab qiladigan
// maydonlarni to'plovchi forma — dizaynda yo'q, lekin haydovchi ro'yxatdan o'tishni
// yakunlashi uchun zarur (aks holda profil yo'q holatda qoladi).
export function DriverProfileSetupPage({ onCreated }: Props) {
  const [truckTypes, setTruckTypes] = useState<TruckType[]>([]);
  const [truckTypeId, setTruckTypeId] = useState<number | null>(null);
  const [truckNumber, setTruckNumber] = useState('');
  const [truckYear, setTruckYear] = useState('');
  const [city, setCity] = useState('');
  const [region, setRegion] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTruckTypes()
      .then((types) => {
        setTruckTypes(types);
        setTruckTypeId((prev) => prev ?? types[0]?.id ?? null);
      })
      .catch(() => setTruckTypes([]));
  }, []);

  async function handleSubmit() {
    if (!truckTypeId) {
      setError('Mashina turini tanlang');
      return;
    }
    if (!truckNumber.trim()) {
      setError("Davlat raqamini kiriting");
      return;
    }
    if (!city.trim()) {
      setError('Shahringizni kiriting');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await createDriverProfile({
        truck_type_id: truckTypeId,
        truck_number: truckNumber.trim(),
        truck_year: truckYear ? Number(truckYear) : undefined,
        current_city: city.trim(),
        current_region: region.trim() || undefined,
      });
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Profil yaratilmadi');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.title}>Haydovchi profili</div>
      <div className={styles.subtitle}>Mashinangiz haqida ma'lumot kiriting — bu buyurtma takliflarini olish uchun kerak.</div>

      <div className={styles.field}>
        <label className={styles.label}>Mashina turi</label>
        <select className={styles.select} value={truckTypeId ?? ''} onChange={(e) => setTruckTypeId(Number(e.target.value))}>
          {truckTypes.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      <div className={styles.row}>
        <div className={styles.field}>
          <label className={styles.label}>Davlat raqami</label>
          <input className={styles.input} value={truckNumber} onChange={(e) => setTruckNumber(e.target.value)} placeholder="01A123BC" />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Ishlab chiqarilgan yili</label>
          <input className={styles.input} value={truckYear} onChange={(e) => setTruckYear(e.target.value)} placeholder="2020" inputMode="numeric" />
        </div>
      </div>

      <div className={styles.row}>
        <div className={styles.field}>
          <label className={styles.label}>Shahar</label>
          <input className={styles.input} value={city} onChange={(e) => setCity(e.target.value)} placeholder="Toshkent" />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Viloyat (ixtiyoriy)</label>
          <input className={styles.input} value={region} onChange={(e) => setRegion(e.target.value)} placeholder="Toshkent viloyati" />
        </div>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      <button className={styles.submitBtn} disabled={submitting} onClick={handleSubmit}>
        {submitting ? 'Yuborilmoqda...' : 'Profilni yaratish'}
      </button>
    </div>
  );
}
