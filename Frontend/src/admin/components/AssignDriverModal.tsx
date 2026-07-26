import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { assignDriverToOrder, getDriver } from '../../api/admin';
import type { AdminDriverListItem, Order } from '../../types/api';
import { Modal } from './Modal';
import { useToast } from './Toast';
import shared from '../shared.module.css';
import styles from './AssignDriverModal.module.css';

interface Props {
  order: Order;
  onClose: () => void;
  /** Muvaffaqiyatli biriktirilgach — ro'yxatni qayta yuklash uchun. */
  onAssigned: () => void;
}

const LOOKUP_DEBOUNCE_MS = 400;

function formatMoney(value: number): string {
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 0 }).format(value);
}

/** Driver ID kiritiladi → haydovchi ma'lumoti ko'rsatiladi → tasdiqlangach biriktiriladi. */
export function AssignDriverModal({ order, onClose, onAssigned }: Props) {
  const toast = useToast();
  const [driverId, setDriverId] = useState('');
  const [driver, setDriver] = useState<AdminDriverListItem | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookingUp, setLookingUp] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Kiritilayotgan ID bo'yicha haydovchini debounce bilan qidiramiz — har bosilgan
  // raqamga so'rov yubormaslik uchun.
  useEffect(() => {
    const raw = driverId.trim();
    setDriver(null);
    setLookupError(null);

    if (!raw) return;
    const id = Number(raw);
    if (!Number.isInteger(id) || id <= 0) {
      setLookupError("Driver ID musbat butun son bo'lishi kerak");
      return;
    }

    let cancelled = false;
    setLookingUp(true);
    const timer = window.setTimeout(() => {
      getDriver(id)
        .then((found) => !cancelled && setDriver(found))
        .catch((err) => {
          if (cancelled) return;
          setLookupError(
            err instanceof ApiError && err.status === 404
              ? `#${id} raqamli haydovchi topilmadi`
              : err instanceof ApiError
                ? err.message
                : 'Haydovchi ma’lumoti olinmadi',
          );
        })
        .finally(() => !cancelled && setLookingUp(false));
    }, LOOKUP_DEBOUNCE_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      window.setTimeout(() => setLookingUp(false), 0);
    };
  }, [driverId]);

  async function confirm() {
    if (!driver || submitting) return;
    setSubmitting(true);
    try {
      const res = await assignDriverToOrder(order.id, driver.driver_id);
      toast.success(
        `Buyurtma #${order.id} ${res.driver.full_name ?? `#${res.driver.driver_id}`} ` +
          `(${res.driver.truck_number}) ga biriktirildi`,
      );
      onAssigned();
      onClose();
    } catch (err) {
      // 404 / 409 (allaqachon biriktirilgan, bloklangan haydovchi) — backend matni ko'rsatiladi
      toast.error(err instanceof ApiError ? err.message : "Biriktirib bo'lmadi");
      setSubmitting(false);
    }
  }

  const blocked = driver?.is_blocked ?? false;

  return (
    <Modal
      title={`Buyurtma #${order.id} — haydovchi biriktirish`}
      onClose={onClose}
      footer={
        <>
          <button className={shared.ghostBtn} onClick={onClose} disabled={submitting}>
            Bekor qilish
          </button>
          <button className={shared.primaryBtn} disabled={!driver || blocked || submitting} onClick={confirm}>
            {submitting ? 'Biriktirilmoqda...' : 'Tasdiqlash'}
          </button>
        </>
      }
    >
      <div className={styles.body}>
        <div className={styles.orderLine}>
          <span className={styles.muted}>Yuk:</span> <strong>{order.cargo_name}</strong>
          {order.driver_id != null && (
            <span className={styles.warnInline}>· hozir #{order.driver_id} haydovchida</span>
          )}
        </div>

        <label className={styles.field}>
          <span className={styles.label}>Driver ID</span>
          <input
            className={styles.input}
            inputMode="numeric"
            autoFocus
            placeholder="Masalan: 1"
            value={driverId}
            onChange={(e) => setDriverId(e.target.value)}
          />
        </label>

        {lookingUp && <div className={styles.muted}>Qidirilmoqda...</div>}
        {lookupError && <div className={styles.error}>{lookupError}</div>}

        {driver && (
          <>
            <div className={styles.card}>
              <div className={styles.cardHead}>
                <div>
                  <div className={styles.name}>{driver.full_name ?? `Haydovchi #${driver.driver_id}`}</div>
                  <div className={styles.sub}>ID #{driver.driver_id}</div>
                </div>
                <span className={blocked ? styles.badgeBlocked : styles.badgeOk}>
                  {blocked ? 'Bloklangan' : driver.is_available ? 'Liniyada' : 'Faol'}
                </span>
              </div>

              <dl className={styles.rows}>
                <div className={styles.row}>
                  <dt>Telefon</dt>
                  <dd>{driver.phone_number ?? '—'}</dd>
                </div>
                <div className={styles.row}>
                  <dt>Davlat raqami</dt>
                  <dd>{driver.truck_number}</dd>
                </div>
                <div className={styles.row}>
                  <dt>Balans</dt>
                  <dd className={driver.balance < 0 ? styles.debt : undefined}>
                    {formatMoney(Number(driver.balance))} UZS
                  </dd>
                </div>
                <div className={styles.row}>
                  <dt>Hujjatlar</dt>
                  <dd>{driver.verification_status === 'approved' ? 'Tasdiqlangan' : driver.verification_status}</dd>
                </div>
              </dl>

              {blocked && (
                <div className={styles.blockNote}>
                  Bloklangan haydovchini biriktirib bo'lmaydi. Sababi: {driver.block_reason || "noma'lum"}.
                  Avval “Haydovchilar → Balans va bloklar” bo'limidan blokdan chiqaring.
                </div>
              )}
            </div>

            {!blocked && (
              <div className={styles.confirmBox}>
                Haqiqatdan ham ushbu haydovchini biriktirmoqchimisiz? Buyurtma holati
                “Qabul qilindi” ga o'tadi va haydovchiga Telegram orqali xabar boradi.
              </div>
            )}
          </>
        )}
      </div>
    </Modal>
  );
}
