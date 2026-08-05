import { useEffect, useState } from 'react';
import { ApiError } from '../api/client';
import { updateOrder } from '../api/orders';
import { listTruckTypes } from '../api/truckTypes';
import type { OrderDetail, OrderUpdateInput, TruckType } from '../types/api';
import {
  fromDateTimeLocalValue,
  maxPickupValue,
  minPickupValue,
  toDateTimeLocalValue,
  validatePickupAt,
} from '../utils/pickupTime';
import { BottomSheetModal } from './BottomSheetModal';
import styles from './OrderEditSheet.module.css';

// Buyurtmani tahrirlash (PATCH /orders/{id}) — faqat yuk ma'lumotlari.
// Narx, status va haydovchi bu yerdan o'zgarmaydi: serverdagi `OrderUpdate` sxemasi
// ularni ATAYLAB qabul qilmaydi (`extra="forbid"`), chunki ilgari shu yo'l bilan
// statusni COMPLETED qilib komissiyani chetlab o'tish mumkin edi.
//
// Faqat o'zgargan maydonlar yuboriladi — teginilmagan maydon serverga bormaydi.

interface Props {
  order: OrderDetail;
  onClose: () => void;
  onSaved: (order: OrderDetail) => void;
}

export function OrderEditSheet({ order, onClose, onSaved }: Props) {
  const [cargoName, setCargoName] = useState(order.cargo_name);
  const [weight, setWeight] = useState(String(order.weight));
  const [volume, setVolume] = useState(order.volume != null ? String(order.volume) : '');
  const [pickupAt, setPickupAt] = useState<Date>(new Date(order.pickup_at));
  const [truckTypeId, setTruckTypeId] = useState(order.required_truck_type_id);
  const [truckTypes, setTruckTypes] = useState<TruckType[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void listTruckTypes()
      .then((list) => !cancelled && setTruckTypes(list))
      .catch(() => {
        // Ro'yxat yuklanmasa ham qolgan maydonlarni tahrirlash mumkin bo'lib qolsin.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const weightNum = Number(weight.replace(',', '.'));
  const volumeNum = volume.trim() === '' ? null : Number(volume.replace(',', '.'));
  const pickupError = validatePickupAt(pickupAt);

  const valid =
    cargoName.trim().length > 0 &&
    Number.isFinite(weightNum) &&
    weightNum > 0 &&
    (volumeNum === null || (Number.isFinite(volumeNum) && volumeNum > 0)) &&
    pickupError === null;

  async function save() {
    if (!valid || saving) return;
    setSaving(true);
    setError(null);

    const patch: OrderUpdateInput = {};
    if (cargoName.trim() !== order.cargo_name) patch.cargo_name = cargoName.trim();
    if (weightNum !== Number(order.weight)) patch.weight = weightNum;
    if (volumeNum !== (order.volume != null ? Number(order.volume) : null) && volumeNum !== null) {
      patch.volume = volumeNum;
    }
    if (pickupAt.toISOString() !== new Date(order.pickup_at).toISOString()) {
      patch.pickup_at = pickupAt.toISOString();
    }
    if (truckTypeId !== order.required_truck_type_id) patch.required_truck_type_id = truckTypeId;

    if (Object.keys(patch).length === 0) {
      onClose();
      setSaving(false);
      return;
    }

    try {
      onSaved(await updateOrder(order.id, patch));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Saqlab bo'lmadi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <BottomSheetModal title="Buyurtmani tahrirlash" onClose={onClose}>
      <div className={styles.form}>
        {error && <div className={styles.error}>{error}</div>}

        <label className={styles.field}>
          <span className={styles.label}>Yuk nomi</span>
          <input
            className={styles.input}
            value={cargoName}
            maxLength={200}
            onChange={(e) => setCargoName(e.target.value)}
          />
        </label>

        <div className={styles.row}>
          <label className={styles.field}>
            <span className={styles.label}>Og‘irligi (t)</span>
            <input
              className={styles.input}
              inputMode="decimal"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
            />
          </label>

          <label className={styles.field}>
            <span className={styles.label}>Hajmi (m³)</span>
            <input
              className={styles.input}
              inputMode="decimal"
              value={volume}
              placeholder="ixtiyoriy"
              onChange={(e) => setVolume(e.target.value)}
            />
          </label>
        </div>

        <label className={styles.field}>
          <span className={styles.label}>Yuklash vaqti</span>
          <input
            className={styles.input}
            type="datetime-local"
            value={toDateTimeLocalValue(pickupAt)}
            min={minPickupValue()}
            max={maxPickupValue()}
            onChange={(e) => {
              const next = fromDateTimeLocalValue(e.target.value);
              if (next) setPickupAt(next);
            }}
          />
          {pickupError && <span className={styles.invalid}>{pickupError}</span>}
        </label>

        {truckTypes.length > 0 && (
          <label className={styles.field}>
            <span className={styles.label}>Transport turi</span>
            <select
              className={styles.input}
              value={truckTypeId}
              onChange={(e) => setTruckTypeId(Number(e.target.value))}
            >
              {truckTypes.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </label>
        )}

        <div className={styles.hint}>
          Narx server tomonida qayta hisoblanadi — masofa va transport turiga qarab.
        </div>

        <button className={styles.submit} disabled={!valid || saving} onClick={save}>
          {saving ? 'Saqlanmoqda...' : 'Saqlash'}
        </button>
      </div>
    </BottomSheetModal>
  );
}
