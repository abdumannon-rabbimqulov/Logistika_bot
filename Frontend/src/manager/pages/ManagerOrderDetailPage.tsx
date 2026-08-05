import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { getManagerOrder, updateManagerOrderStatus } from '../../api/manager';
import { StatusBadge } from '../../admin/components/StatusBadge';
import { useToast } from '../../admin/components/Toast';
import shared from '../../admin/shared.module.css';
import type { ManagerOrderDetail, OrderStatus } from '../../types/api';
import { AssignTruckModal } from '../components/AssignTruckModal';
import styles from './ManagerOrderDetailPage.module.css';

// Bitta buyurtma: marshrut nuqtalari, holatni yangilash va mashina biriktirish.
// Narx bu ekranda YO'Q — backend uni menejerga umuman qaytarmaydi.

const STATUSES: OrderStatus[] = [
  'SCHEDULED',
  'PENDING',
  'ACCEPTED',
  'IN_PROGRESS',
  'COMPLETED',
  'CANCELLED',
];

const WAYPOINT_TYPE_LABELS: Record<string, string> = {
  PICKUP: 'Yuklash',
  DELIVERY: 'Tushirish',
  TRANSIT: 'Oraliq',
};

const WAYPOINT_STATUS_LABELS: Record<string, string> = {
  PENDING: 'Kutilmoqda',
  ARRIVED: 'Yetib bordi',
  COMPLETED: 'Bajarildi',
  SKIPPED: "O'tkazib yuborildi",
};

function formatDateTime(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('uz-UZ');
}

export function ManagerOrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const toast = useToast();

  const [order, setOrder] = useState<ManagerOrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);

  const load = useCallback(async () => {
    if (!orderId) return;
    try {
      setOrder(await getManagerOrder(Number(orderId)));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Buyurtma yuklanmadi');
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function changeStatus(status: OrderStatus) {
    if (!order || busy || status === order.status) return;
    setBusy(true);
    try {
      setOrder(await updateManagerOrderStatus(order.id, status));
      toast.success('Holat yangilandi');
    } catch (err) {
      // `services/order_flow.py` ruxsat bermagan o'tishda 400 keladi — sababi
      // xabar matnida bo'ladi (masalan yakunlangan buyurtmani qayta ochish).
      toast.error(err instanceof ApiError ? err.message : "Holat o'zgartirilmadi");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div className={shared.page}>
        <div className={styles.placeholder}>Yuklanmoqda...</div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className={shared.page}>
        <div className={shared.errorBanner}>{error ?? 'Buyurtma topilmadi'}</div>
        <button className={shared.ghostBtn} onClick={() => navigate('/manager/orders')}>
          ← Buyurtmalarga qaytish
        </button>
      </div>
    );
  }

  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <button className={styles.backLink} onClick={() => navigate('/manager/orders')}>
            ← Buyurtmalar
          </button>
          <h1 className={shared.pageTitle}>
            Buyurtma #{order.id} <StatusBadge status={order.status} />
          </h1>
          <div className={shared.pageSub}>{order.cargo_name}</div>
        </div>

        <div className={styles.headActions}>
          <select
            className={shared.select}
            value={order.status}
            disabled={busy}
            onChange={(e) => void changeStatus(e.target.value as OrderStatus)}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <button className={shared.primaryBtn} disabled={busy} onClick={() => setAssignOpen(true)}>
            {order.driver_id != null ? 'Mashinani almashtirish' : 'Mashina biriktirish'}
          </button>
        </div>
      </div>

      {order.overload_warning && (
        <div className={shared.errorBanner}>{order.overload_warning}</div>
      )}

      <div className={styles.grid}>
        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Yuk</h2>
          <dl className={styles.dl}>
            <dt>Nomi</dt>
            <dd>{order.cargo_name}</dd>
            <dt>Og‘irlik</dt>
            <dd>{order.weight} t</dd>
            <dt>Hajm</dt>
            <dd>{order.volume != null ? `${order.volume} m³` : '—'}</dd>
            <dt>Kerakli transport turi</dt>
            <dd>#{order.required_truck_type_id}</dd>
            <dt>Umumiy masofa</dt>
            <dd>{order.total_distance_km != null ? `${order.total_distance_km} km` : '—'}</dd>
          </dl>
        </div>

        <div className={styles.card}>
          <h2 className={styles.cardTitle}>Tafsilotlar</h2>
          <dl className={styles.dl}>
            <dt>Buyurtmachi</dt>
            <dd>#{order.customer_id}</dd>
            <dt>Haydovchi</dt>
            <dd>
              {order.driver_id != null ? (
                `#${order.driver_id}`
              ) : (
                <span className={styles.unassigned}>Biriktirilmagan</span>
              )}
            </dd>
            <dt>Yuklash vaqti</dt>
            <dd>{formatDateTime(order.pickup_at)}</dd>
            <dt>Jo‘nash vaqti</dt>
            <dd>{formatDateTime(order.departure_at)}</dd>
            <dt>Qidiruv bosqichi</dt>
            <dd>{order.dispatch_round}</dd>
            <dt>Yaratilgan</dt>
            <dd>{formatDateTime(order.created_at)}</dd>
            {order.cancelled_at && (
              <>
                <dt>Bekor qilingan</dt>
                <dd>
                  {formatDateTime(order.cancelled_at)}
                  {order.cancel_reason && ` — ${order.cancel_reason}`}
                </dd>
              </>
            )}
          </dl>
        </div>
      </div>

      <div className={styles.card}>
        <h2 className={styles.cardTitle}>Marshrut</h2>
        {order.waypoints.length === 0 ? (
          <div className={styles.placeholder}>Nuqtalar yo'q</div>
        ) : (
          <ol className={styles.waypoints}>
            {order.waypoints
              .slice()
              .sort((a, b) => a.sequence - b.sequence)
              .map((wp) => (
                <li key={wp.id} className={styles.waypoint}>
                  <div className={styles.wpHead}>
                    <span className={styles.wpType}>
                      {WAYPOINT_TYPE_LABELS[wp.type] ?? wp.type}
                    </span>
                    <span className={styles[`wp_${wp.status}`] ?? styles.wpStatus}>
                      {WAYPOINT_STATUS_LABELS[wp.status] ?? wp.status}
                    </span>
                  </div>
                  <div className={styles.wpAddress}>{wp.address ?? '—'}</div>
                  {(wp.contact_name || wp.contact_phone) && (
                    <div className={styles.wpContact}>
                      {wp.contact_name}
                      {wp.contact_phone && ` · ${wp.contact_phone}`}
                    </div>
                  )}
                  <div className={styles.wpTimes}>
                    Yetib bordi: {formatDateTime(wp.arrived_at)} · Bajarildi:{' '}
                    {formatDateTime(wp.completed_at)}
                  </div>
                </li>
              ))}
          </ol>
        )}
      </div>

      {assignOpen && (
        <AssignTruckModal
          orderId={order.id}
          onClose={() => setAssignOpen(false)}
          onAssigned={(updated) => {
            setOrder(updated);
            setAssignOpen(false);
            toast.success('Mashina biriktirildi');
          }}
        />
      )}
    </div>
  );
}
