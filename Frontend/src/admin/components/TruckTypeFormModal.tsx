import { useRef, useState } from 'react';
import { ApiError } from '../../api/client';
import {
  createTruckType,
  staticFileUrl,
  updateTruckType,
  uploadTruckTypeImage,
} from '../../api/truckTypes';
import type { TruckType, TruckTypeInput } from '../../types/api';
import { Modal } from './Modal';
import styles from './TruckTypeFormModal.module.css';

interface Props {
  editing: TruckType | null;
  onClose: () => void;
  onSaved: () => void;
}

interface FormState {
  name: string;
  max_weight: string;
  max_volume: string;
  length: string;
  width: string;
  height: string;
  pallet_capacity: string;
  base_price: string;
  price_per_km: string;
  min_price: string;
  image_url: string;
  description: string;
  is_active: boolean;
}

function initialState(t: TruckType | null): FormState {
  const num = (v: number | null | undefined) => (v == null ? '' : String(v));
  return {
    name: t?.name ?? '',
    max_weight: num(t?.max_weight),
    max_volume: num(t?.max_volume),
    length: num(t?.length),
    width: num(t?.width),
    height: num(t?.height),
    pallet_capacity: num(t?.pallet_capacity),
    base_price: num(t?.base_price),
    price_per_km: num(t?.price_per_km),
    min_price: num(t?.min_price),
    image_url: t?.image_url ?? '',
    description: t?.description ?? '',
    is_active: t?.is_active ?? true,
  };
}

function toNumOrNull(v: string): number | null {
  const s = v.trim();
  if (s === '') return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

export function TruckTypeFormModal({ editing, onClose, onSaved }: Props) {
  const [form, setForm] = useState(initialState(editing));
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [previewFailed, setPreviewFailed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    if (key === 'image_url') setPreviewFailed(false);
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      set('image_url', await uploadTruckTypeImage(file));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Rasm yuklab bo'lmadi");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  async function handleSubmit() {
    setError(null);
    if (!form.name.trim()) return setError('Nomni kiriting');
    const maxWeight = toNumOrNull(form.max_weight);
    const maxVolume = toNumOrNull(form.max_volume);
    if (maxWeight == null || maxWeight <= 0) return setError("Maksimal og'irlik 0 dan katta bo'lishi kerak");
    if (maxVolume == null || maxVolume <= 0) return setError('Maksimal hajm 0 dan katta bo’lishi kerak');
    const basePrice = toNumOrNull(form.base_price) ?? 0;
    const pricePerKm = toNumOrNull(form.price_per_km) ?? 0;
    if (basePrice < 0 || pricePerKm < 0) return setError('Narx manfiy bo’lishi mumkin emas');

    const payload: TruckTypeInput = {
      name: form.name.trim(),
      max_weight: maxWeight,
      max_volume: maxVolume,
      length: toNumOrNull(form.length),
      width: toNumOrNull(form.width),
      height: toNumOrNull(form.height),
      pallet_capacity: toNumOrNull(form.pallet_capacity),
      base_price: basePrice,
      price_per_km: pricePerKm,
      min_price: toNumOrNull(form.min_price),
      image_url: form.image_url.trim() || null,
      description: form.description.trim() || null,
      is_active: form.is_active,
    };

    setSubmitting(true);
    try {
      if (editing) await updateTruckType(editing.id, payload);
      else await createTruckType(payload);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Saqlab bo'lmadi");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      title={editing ? 'Transport turini tahrirlash' : "Yangi transport turi"}
      onClose={onClose}
      footer={
        <>
          <button className={styles.cancelBtn} onClick={onClose} disabled={submitting}>
            Bekor qilish
          </button>
          <button className={styles.saveBtn} onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Saqlanmoqda...' : 'Saqlash'}
          </button>
        </>
      }
    >
      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.field}>
        <label className={styles.label}>Nomi *</label>
        <input className={styles.input} value={form.name} onChange={(e) => set('name', e.target.value)} placeholder="Isuzu tent" />
      </div>

      <div className={styles.grid2}>
        <div className={styles.field}>
          <label className={styles.label}>Maks. og'irlik (t) *</label>
          <input className={styles.input} type="number" inputMode="decimal" value={form.max_weight} onChange={(e) => set('max_weight', e.target.value)} />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Maks. hajm (m³) *</label>
          <input className={styles.input} type="number" inputMode="decimal" value={form.max_volume} onChange={(e) => set('max_volume', e.target.value)} />
        </div>
      </div>

      {/* NARX — buyurtma narxi shu tariflardan hisoblanadi */}
      <div className={styles.priceBox}>
        <div className={styles.priceTitle}>Narx tarifi (UZS)</div>
        <div className={styles.grid3}>
          <div className={styles.field}>
            <label className={styles.label}>Boshlang'ich</label>
            <input className={styles.input} type="number" inputMode="numeric" value={form.base_price} onChange={(e) => set('base_price', e.target.value)} />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>1 km narxi</label>
            <input className={styles.input} type="number" inputMode="numeric" value={form.price_per_km} onChange={(e) => set('price_per_km', e.target.value)} />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Minimal (pol)</label>
            <input className={styles.input} type="number" inputMode="numeric" value={form.min_price} onChange={(e) => set('min_price', e.target.value)} />
          </div>
        </div>
        <div className={styles.priceHint}>Narx = boshlang'ich + (1 km narxi × masofa), lekin minimaldan kam emas.</div>
      </div>

      <div className={styles.grid3}>
        <div className={styles.field}>
          <label className={styles.label}>Uzunlik (m)</label>
          <input className={styles.input} type="number" inputMode="decimal" value={form.length} onChange={(e) => set('length', e.target.value)} />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Kenglik (m)</label>
          <input className={styles.input} type="number" inputMode="decimal" value={form.width} onChange={(e) => set('width', e.target.value)} />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Balandlik (m)</label>
          <input className={styles.input} type="number" inputMode="decimal" value={form.height} onChange={(e) => set('height', e.target.value)} />
        </div>
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Palletlar soni</label>
        <input className={styles.input} type="number" inputMode="numeric" value={form.pallet_capacity} onChange={(e) => set('pallet_capacity', e.target.value)} />
      </div>

      {/* RASM — fayl yuklanadi (POST /drivers/truck-types/image) yoki URL qo'lda kiritiladi */}
      <div className={styles.field}>
        <label className={styles.label}>Rasm</label>
        <div className={styles.imageRow}>
          {form.image_url && !previewFailed ? (
            <img
              className={styles.imagePreview}
              src={staticFileUrl(form.image_url)}
              alt=""
              onError={() => setPreviewFailed(true)}
            />
          ) : (
            <div className={styles.imagePlaceholder}>{form.image_url ? 'ochilmadi' : 'rasm yo‘q'}</div>
          )}
          <div className={styles.imageControls}>
            <input
              ref={fileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif"
              className={styles.fileInput}
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            <button
              type="button"
              className={styles.uploadBtn}
              disabled={uploading}
              onClick={() => fileRef.current?.click()}
            >
              {uploading ? 'Yuklanmoqda...' : 'Rasm yuklash'}
            </button>
            <input
              className={styles.input}
              value={form.image_url}
              onChange={(e) => set('image_url', e.target.value)}
              placeholder="yoki URL kiriting"
            />
            {form.image_url && (
              <button type="button" className={styles.clearBtn} onClick={() => set('image_url', '')}>
                Rasmni olib tashlash
              </button>
            )}
          </div>
        </div>
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Izoh</label>
        <input className={styles.input} value={form.description} onChange={(e) => set('description', e.target.value)} placeholder="Ixtiyoriy" />
      </div>

      <label className={styles.switchRow}>
        <input type="checkbox" checked={form.is_active} onChange={(e) => set('is_active', e.target.checked)} />
        <span>Faol (buyurtma yaratishda tanlash mumkin)</span>
      </label>
    </Modal>
  );
}
