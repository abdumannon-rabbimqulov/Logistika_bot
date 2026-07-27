import { useState } from 'react';
import { ApiError } from '../../api/client';
import { updateAdminOrder } from '../../api/admin';
import type { AdminOrderUpdate, Order, OrderStatus } from '../../types/api';
import { Modal } from './Modal';
import { OrderWaypointsPanel } from './OrderWaypointsPanel';
import shared from '../shared.module.css';
import styles from './OrderEditModal.module.css';

interface Props {
  order: Order;
  onClose: () => void;
  onSaved: (updated: Order) => void;
}

const STATUSES: { value: OrderStatus; label: string }[] = [
  { value: 'PENDING', label: 'Qidirilmoqda' },
  { value: 'SCHEDULED', label: 'Rejalashtirilgan' },
  { value: 'ACCEPTED', label: 'Qabul qilindi' },
  { value: 'IN_PROGRESS', label: "Yo'lda" },
  { value: 'COMPLETED', label: 'Yakunlandi' },
  { value: 'CANCELLED', label: 'Bekor qilindi' },
];

/** Admin buyurtmani tahrirlaydi — PATCH /system/orders/{id}. */
export function OrderEditModal({ order, onClose, onSaved }: Props) {
  const [status, setStatus] = useState<OrderStatus>(order.status as OrderStatus);
  const [cargoName, setCargoName] = useState(order.cargo_name ?? '');
  const [price, setPrice] = useState(String(order.price ?? ''));
  const [weight, setWeight] = useState(String(order.weight ?? ''));
  const [currency, setCurrency] = useState(order.currency ?? 'UZS');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const payload: AdminOrderUpdate = {};
  if (status !== order.status) payload.status = status;
  if (cargoName.trim() && cargoName.trim() !== order.cargo_name) payload.cargo_name = cargoName.trim();
  if (price.trim() && Number(price) !== Number(order.price)) payload.price = Number(price);
  if (weight.trim() && Number(weight) !== Number(order.weight)) payload.weight = Number(weight);
  if (currency.trim() && currency.trim() !== order.currency) payload.currency = currency.trim();

  const dirty = Object.keys(payload).length > 0;
  const numbersValid =
    (!price.trim() || Number(price) > 0) && (!weight.trim() || Number(weight) > 0);

  async function save() {
    if (!dirty || saving || !numbersValid) return;
    setSaving(true);
    setError(null);
    try {
      onSaved(await updateAdminOrder(order.id, payload));
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Saqlab bo'lmadi");
    } finally {
      setSaving(false);
    }
  }

  const willComplete = status === 'COMPLETED' && order.status !== 'COMPLETED';

  return (
    <Modal
      title={`Buyurtma #${order.id} — tahrirlash`}
      onClose={onClose}
      footer={
        <>
          <button className={shared.ghostBtn} onClick={onClose}>
            Bekor qilish
          </button>
          <button className={shared.primaryBtn} disabled={!dirty || !numbersValid || saving} onClick={save}>
            {saving ? 'Saqlanmoqda...' : 'Saqlash'}
          </button>
        </>
      }
    >
      <div className={styles.body}>
        <label className={styles.field}>
          <span className={styles.label}>Yuk nomi</span>
          <input className={styles.input} value={cargoName} onChange={(e) => setCargoName(e.target.value)} />
        </label>

        <div className={styles.row}>
          <label className={styles.field}>
            <span className={styles.label}>Narx</span>
            <input
              className={styles.input}
              inputMode="decimal"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
            />
          </label>
          <label className={styles.fieldNarrow}>
            <span className={styles.label}>Valyuta</span>
            <input className={styles.input} value={currency} onChange={(e) => setCurrency(e.target.value)} />
          </label>
          <label className={styles.fieldNarrow}>
            <span className={styles.label}>Og‘irlik (t)</span>
            <input
              className={styles.input}
              inputMode="decimal"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
            />
          </label>
        </div>

        <label className={styles.field}>
          <span className={styles.label}>Holat</span>
          <select
            className={styles.input}
            value={status}
            onChange={(e) => setStatus(e.target.value as OrderStatus)}
          >
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>

        {willComplete && (
          <div className={styles.notice}>
            “Yakunlandi” qilinganda haydovchi balansidan komissiya avtomatik yechiladi
            {order.driver_id ? ` (haydovchi #${order.driver_id})` : ' — bu buyurtmada haydovchi yo‘q, komissiya yechilmaydi'}.
          </div>
        )}

        <OrderWaypointsPanel order={order} onChanged={onSaved} />

        {!numbersValid && <div className={styles.invalid}>Narx va og‘irlik 0 dan katta bo‘lishi kerak</div>}
        {error && <div className={shared.errorBanner}>{error}</div>}
      </div>
    </Modal>
  );
}
