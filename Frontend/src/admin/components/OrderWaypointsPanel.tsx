import { useState } from 'react';
import { ApiError } from '../../api/client';
import { updateWaypoint } from '../../api/orders';
import type { Order, OrderWaypoint, WaypointStatus } from '../../types/api';
import shared from '../shared.module.css';
import styles from './OrderWaypointsPanel.module.css';

interface Props {
  order: Order;
  onChanged: (updated: Order) => void;
}

const WAYPOINT_STATUS_LABEL: Record<WaypointStatus, string> = {
  PENDING: 'Kutilmoqda',
  ARRIVED: 'Yetib keldi',
  COMPLETED: 'Yakunlandi',
  SKIPPED: 'Tashlab ketildi',
};

const WAYPOINT_TYPE_LABEL: Record<string, string> = {
  PICKUP: 'Yuk ortish',
  DELIVERY: 'Yetkazish',
  TRANSIT: 'Oraliq',
};

/** Keyingi qadam — haydovchi ilovasidagi bilan bir xil qoida. */
function nextStatus(wp: OrderWaypoint): WaypointStatus | null {
  if (wp.status === 'PENDING') return 'ARRIVED';
  if (wp.status === 'ARRIVED') return 'COMPLETED';
  return null;
}

function formatTime(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleString('uz-UZ', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Marshrut nuqtalari va ularni qo'lda tasdiqlash.
 *
 * Haydovchi har bir qadamni GPS bilan tasdiqlaydi, lekin GPS nosoz bo'lishi mumkin
 * (yopiq ombor, telefon eskirgan, ruxsat berilmagan). Shunday holatda haydovchi
 * buyurtmada qotib qolmasligi uchun admin qadamni qo'lda tasdiqlaydi — sabab
 * majburiy va u nuqtaga yozib qo'yiladi (kim tasdiqlagani bilan birga).
 */
export function OrderWaypointsPanel({ order, onChanged }: Props) {
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reasonFor, setReasonFor] = useState<number | null>(null);
  const [reason, setReason] = useState('');

  const waypoints = order.waypoints ?? [];
  if (waypoints.length === 0) return null;

  // Faqat birinchi tugallanmagan nuqta ustida ish olib boriladi (backend ham shu
  // ketma-ketlikni majburlaydi) — aks holda tugma bosiladi-yu, 422 qaytadi.
  const current = waypoints.find((w) => w.status !== 'COMPLETED' && w.status !== 'SKIPPED');

  async function confirm(wp: OrderWaypoint, status: WaypointStatus) {
    if (!reason.trim()) {
      setError('Qo‘lda tasdiqlash uchun sabab yozilishi shart');
      return;
    }
    setBusyId(wp.id);
    setError(null);
    try {
      const updated = await updateWaypoint(order.id, wp.id, {
        status,
        override_reason: reason.trim(),
      });
      setReasonFor(null);
      setReason('');
      // Javob OrderDetail — ro'yxatdagi Order bilan mos maydonlarga ega.
      onChanged(updated as unknown as Order);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Tasdiqlab bo‘lmadi');
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className={styles.panel}>
      <div className={styles.heading}>Marshrut nuqtalari</div>

      <ol className={styles.list}>
        {waypoints.map((wp) => {
          const target = nextStatus(wp);
          const isCurrent = current?.id === wp.id;
          const canConfirm = isCurrent && target !== null;
          return (
            <li key={wp.id} className={styles.item}>
              <div className={styles.itemHead}>
                <span className={`${styles.badge} ${styles[`badge_${wp.status}`] ?? ''}`}>
                  {WAYPOINT_STATUS_LABEL[wp.status]}
                </span>
                <span className={styles.type}>{WAYPOINT_TYPE_LABEL[wp.type] ?? wp.type}</span>
                {isCurrent && <span className={styles.current}>joriy</span>}
              </div>

              <div className={styles.address}>{wp.address ?? 'Manzil ko‘rsatilmagan'}</div>

              {(wp.arrived_at || wp.completed_at) && (
                <div className={styles.meta}>
                  {wp.arrived_at && <span>Yetib keldi: {formatTime(wp.arrived_at)}</span>}
                  {wp.completed_at && <span>Yakunladi: {formatTime(wp.completed_at)}</span>}
                  {wp.confirmed_distance_m != null && (
                    <span>
                      Nuqtadan: {wp.confirmed_distance_m} m
                      {wp.confirmed_accuracy_m != null && ` (±${wp.confirmed_accuracy_m} m)`}
                    </span>
                  )}
                </div>
              )}

              {wp.override_reason && (
                <div className={styles.override}>
                  Qo‘lda tasdiqlangan
                  {wp.override_by_user_id != null && ` (admin #${wp.override_by_user_id})`}: {wp.override_reason}
                </div>
              )}

              {canConfirm && (
                reasonFor === wp.id ? (
                  <div className={styles.confirmBox}>
                    <input
                      className={styles.reasonInput}
                      placeholder="Sabab (masalan: haydovchining GPS'i ishlamadi)"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      autoFocus
                    />
                    <div className={styles.confirmActions}>
                      <button
                        className={shared.ghostBtn}
                        onClick={() => {
                          setReasonFor(null);
                          setReason('');
                          setError(null);
                        }}
                      >
                        Bekor
                      </button>
                      <button
                        className={shared.primaryBtn}
                        disabled={busyId === wp.id || !reason.trim()}
                        onClick={() => confirm(wp, target)}
                      >
                        {busyId === wp.id
                          ? 'Tasdiqlanmoqda...'
                          : `"${WAYPOINT_STATUS_LABEL[target]}" deb belgilash`}
                      </button>
                    </div>
                  </div>
                ) : (
                  <button
                    className={styles.overrideBtn}
                    onClick={() => {
                      setReasonFor(wp.id);
                      setError(null);
                    }}
                  >
                    Qo‘lda tasdiqlash
                  </button>
                )
              )}
            </li>
          );
        })}
      </ol>

      {error && <div className={shared.errorBanner}>{error}</div>}
    </div>
  );
}
