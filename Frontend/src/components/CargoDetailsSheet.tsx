import { useState } from 'react';
import {
  describePickupAt,
  fromDateTimeLocalValue,
  maxPickupValue,
  minPickupValue,
  PICKUP_PRESETS,
  toDateTimeLocalValue,
  validatePickupAt,
} from '../utils/pickupTime';
import type { UnloadingMode } from '../types/api';
import { BottomSheetModal } from './BottomSheetModal';
import styles from './CargoDetailsSheet.module.css';

export interface CargoDetails {
  cargoName: string;
  weight: number;
  volume?: number;
  /** Yuk tayyor bo'ladigan payt — backendga ISO 8601 bo'lib ketadi (`pickup_at`). */
  pickupAt: Date;
  /** Manzilda tushirish sharti — ixtiyoriy, tanlanmasa yuborilmaydi. */
  unloadingMode?: UnloadingMode;
  /** Faqat "bir necha soat" varianti bilan (backend aks holda 422 qaytaradi). */
  unloadingWaitHours?: number;
}

// Tushirish shartlari — mijoz faqat BITTASINI tanlaydi va tanlamasligi ham mumkin.
// Matnlar haydovchi ko'radigan qilib yozilgan: uning uchun bu reysdan keyin mashina
// qancha band bo'lishini bildiradi.
const UNLOADING_OPTIONS: { value: UnloadingMode; label: string }[] = [
  { value: 'IMMEDIATE', label: "O'sha zahoti tushirish" },
  { value: 'HOURS', label: 'Bir necha soat kutish' },
  { value: 'DAY', label: 'Kun kutish' },
];

// `MAX_UNLOADING_WAIT_HOURS` (order/schemas.py) bilan bir xil: undan oshsa bu
// allaqachon "kun kutish" varianti.
const MAX_WAIT_HOURS = 24;

/** Tanlangan shartning qisqa izohi — "Yuk qachon tayyor" qismidagi kabi, foydalanuvchi
 *  yuborishdan oldin nima tanlaganini bir qatorda ko'rib tursin. */
function describeUnloading(mode: UnloadingMode, waitHours: string): string {
  if (mode === 'HOURS') {
    const hours = waitHours.trim();
    return hours ? `${hours} soat kutish` : 'Bir necha soat kutish';
  }
  return UNLOADING_OPTIONS.find((o) => o.value === mode)?.label ?? '—';
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
  // Standart holat — "Hozir". Ilgari vaqt umuman so'ralmasdi va buyurtma har doim
  // "darhol tayyor" bo'lib ketardi (OrderPage `new Date()` yozib yuborardi).
  const [pickupAt, setPickupAt] = useState<Date>(() => new Date());
  // Kalendar faqat "Boshqa vaqt" tanlanganda ochiladi — odatiy holat uchun
  // bitta bosish yetarli bo'lsin.
  const [customOpen, setCustomOpen] = useState(false);
  // Tushirish sharti — ixtiyoriy, shuning uchun standart holat `null` ("tanlanmagan").
  const [unloadingMode, setUnloadingMode] = useState<UnloadingMode | null>(null);
  const [waitHours, setWaitHours] = useState('');

  function selectUnloadingMode(mode: UnloadingMode) {
    // Tanlangan variantni qayta bosish — bekor qilish. Aks holda foydalanuvchi bir
    // marta bosgandan keyin "hech qanday shart yo'q" holatiga qaytolmasdi.
    const next = unloadingMode === mode ? null : mode;
    setUnloadingMode(next);
    if (next !== 'HOURS') setWaitHours('');
    setError(null);
  }

  function selectPreset(build: () => Date) {
    setPickupAt(build());
    setCustomOpen(false);
    setError(null);
  }

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
    // "Hozir" tanlanib forma uzoq ochiq turgan bo'lsa vaqt o'tib ketishi mumkin —
    // shuning uchun yuborishdan oldin qayta tekshiriladi (server ham tekshiradi).
    const pickupError = validatePickupAt(pickupAt);
    if (pickupError) {
      setError(pickupError);
      return;
    }
    // Kutish soati ixtiyoriy: bo'sh qoldirilsa shart "bir necha soat" bo'lib qolaveradi.
    const waitNum = waitHours.trim() ? Number(waitHours.replace(',', '.')) : undefined;
    if (unloadingMode === 'HOURS' && waitNum !== undefined) {
      if (!Number.isInteger(waitNum) || waitNum < 1 || waitNum > MAX_WAIT_HOURS) {
        setError(`Kutish vaqtini 1 dan ${MAX_WAIT_HOURS} soatgacha butun son bilan kiriting`);
        return;
      }
    }
    setError(null);
    const volumeNum = volume ? Number(volume.replace(',', '.')) : undefined;
    onSubmit({
      cargoName: cargoName.trim(),
      weight: weightNum,
      volume: volumeNum && volumeNum > 0 ? volumeNum : undefined,
      pickupAt,
      unloadingMode: unloadingMode ?? undefined,
      unloadingWaitHours: unloadingMode === 'HOURS' ? waitNum : undefined,
    });
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
      <div className={styles.field}>
        <label className={styles.label}>Yuk qachon tayyor bo'ladi?</label>
        <div className={styles.presets}>
          {PICKUP_PRESETS.map((preset) => {
            const candidate = preset.build();
            // Tanlangan variant ajratib ko'rsatiladi. Daqiqagacha aniqlik shart emas —
            // "Hozir" har renderda yangi vaqt beradi, shuning uchun taqqoslash
            // daqiqa darajasida qilinadi.
            const active =
              !customOpen &&
              Math.abs(candidate.getTime() - pickupAt.getTime()) < 60_000;
            return (
              <button
                key={preset.label}
                type="button"
                className={active ? styles.presetActive : styles.preset}
                onClick={() => selectPreset(preset.build)}
              >
                {preset.label}
              </button>
            );
          })}
          <button
            type="button"
            className={customOpen ? styles.presetActive : styles.preset}
            onClick={() => setCustomOpen(true)}
          >
            Boshqa vaqt
          </button>
        </div>

        {customOpen && (
          <input
            className={styles.input}
            type="datetime-local"
            value={toDateTimeLocalValue(pickupAt)}
            min={minPickupValue()}
            max={maxPickupValue()}
            onChange={(e) => {
              const next = fromDateTimeLocalValue(e.target.value);
              if (next) {
                setPickupAt(next);
                setError(validatePickupAt(next));
              }
            }}
          />
        )}

        <div className={styles.pickupSummary}>Tanlandi: {describePickupAt(pickupAt)}</div>
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Manzilda yukni tushirish (ixtiyoriy)</label>
        <div className={styles.presets}>
          {UNLOADING_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              className={unloadingMode === option.value ? styles.presetActive : styles.preset}
              onClick={() => selectUnloadingMode(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>

        {unloadingMode === 'HOURS' && (
          <input
            className={styles.input}
            inputMode="numeric"
            value={waitHours}
            onChange={(e) => setWaitHours(e.target.value)}
            placeholder={`Taxminiy kutish, soat (1–${MAX_WAIT_HOURS}) — ixtiyoriy`}
          />
        )}

        <div className={styles.pickupSummary}>
          {unloadingMode === null
            ? "Tanlanmagan — haydovchiga qo'shimcha shart qo'yilmaydi"
            : `Tanlandi: ${describeUnloading(unloadingMode, waitHours)}`}
        </div>
      </div>

      {(error || apiError) && <div className={styles.error}>{error ?? apiError}</div>}
      <button className={styles.submitBtn} onClick={handleSubmit} disabled={submitting}>
        {submitting ? 'Yuborilmoqda...' : 'Tasdiqlash'}
      </button>
    </BottomSheetModal>
  );
}
