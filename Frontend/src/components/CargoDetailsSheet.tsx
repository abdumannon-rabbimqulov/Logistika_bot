import { useState } from 'react';
import { BottomSheetModal } from './BottomSheetModal';
import styles from './CargoDetailsSheet.module.css';

export interface CargoDetails {
  cargoName: string;
  weight: number;
  volume?: number;
}

interface Props {
  onSubmit: (details: CargoDetails) => void;
  onClose: () => void;
  submitting: boolean;
  apiError?: string | null;
}

// Dizaynda yuk tafsilotlari uchun alohida ekran yo'q, lekin backend `OrderCreate` buni talab
// qiladi (cargo_name, weight) — shuning uchun "Buyurtma berish" bosilganda shu kichik forma
// so'raladi (minimal, dizayn tokenlariga mos).
export function CargoDetailsSheet({ onSubmit, onClose, submitting, apiError }: Props) {
  const [cargoName, setCargoName] = useState('');
  const [weight, setWeight] = useState('');
  const [volume, setVolume] = useState('');
  const [error, setError] = useState<string | null>(null);

  function handleSubmit() {
    const weightNum = Number(weight.replace(',', '.'));
    if (!cargoName.trim()) {
      setError("Yuk nomini kiriting");
      return;
    }
    if (!weightNum || weightNum <= 0) {
      setError("Yuk og'irligini to'g'ri kiriting");
      return;
    }
    setError(null);
    const volumeNum = volume ? Number(volume.replace(',', '.')) : undefined;
    onSubmit({ cargoName: cargoName.trim(), weight: weightNum, volume: volumeNum && volumeNum > 0 ? volumeNum : undefined });
  }

  return (
    <BottomSheetModal title="Yuk tafsilotlari" onClose={onClose}>
      <div className={styles.field}>
        <label className={styles.label}>Yuk nomi</label>
        <input className={styles.input} value={cargoName} onChange={(e) => setCargoName(e.target.value)} placeholder="Masalan: mebel, oziq-ovqat..." />
      </div>
      <div className={styles.row}>
        <div className={styles.field}>
          <label className={styles.label}>Og'irligi (tonna)</label>
          <input
            className={styles.input}
            inputMode="decimal"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            placeholder="1.5"
          />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Hajmi, m³ (ixtiyoriy)</label>
          <input
            className={styles.input}
            inputMode="decimal"
            value={volume}
            onChange={(e) => setVolume(e.target.value)}
            placeholder="—"
          />
        </div>
      </div>
      {(error || apiError) && <div className={styles.error}>{error ?? apiError}</div>}
      <button className={styles.submitBtn} onClick={handleSubmit} disabled={submitting}>
        {submitting ? 'Yuborilmoqda...' : 'Tasdiqlash'}
      </button>
    </BottomSheetModal>
  );
}
