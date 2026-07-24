import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { getOrder, updateOrderStatus } from '../api/orders';
import { BackIcon, PhoneIcon, WeightIcon } from '../components/icons';
import type { OrderDetail, OrderStatus, OrderWaypoint, WaypointType } from '../types/api';
import { formatPrice, statusLabel } from '../utils/format';
import styles from './DriverActiveOrderPage.module.css';

const WAYPOINT_TYPE_LABEL: Record<WaypointType, string> = {
  PICKUP: 'Yuk ortish',
  DELIVERY: 'Yetkazish',
  TRANSIT: 'Oraliq nuqta',
};

// Joriy statusdan keyingi qadam: qaysi tugma va qaysi yangi status.
const NEXT_STEP: Partial<Record<OrderStatus, { label: string; next: OrderStatus }>> = {
  ACCEPTED: { label: 'Yukni oldim', next: 'IN_PROGRESS' },
  IN_PROGRESS: { label: 'Yetkazdim', next: 'COMPLETED' },
};

function contactOf(order: OrderDetail): OrderWaypoint | null {
  const pickup = order.waypoints.find((w) => w.type === 'PICKUP' && w.contact_phone);
  return pickup ?? order.waypoints.find((w) => w.contact_phone) ?? order.origin ?? null;
}

export function DriverActiveOrderPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  const load = useCallback(async () => {
    if (!orderId) return;
    try {
      const detail = await getOrder(Number(orderId));
      setOrder(detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Buyurtma yuklanmadi');
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAdvance() {
    if (!order) return;
    const step = NEXT_STEP[order.status];
    if (!step) return;
    setUpdating(true);
    setError(null);
    try {
      await updateOrderStatus(order.id, step.next);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Holatni o'zgartirib bo'lmadi");
    } finally {
      setUpdating(false);
    }
  }

  if (loading) {
    return (
      <div className={styles.center}>
        <div className={styles.spinner} />
      </div>
    );
  }

  if (!order) {
    return (
      <div className={styles.center}>
        <div className={styles.errorBanner}>{error ?? 'Buyurtma topilmadi'}</div>
        <button className={styles.backLink} onClick={() => navigate('/')}>Bosh sahifaga</button>
      </div>
    );
  }

  const contact = contactOf(order);
  const step = NEXT_STEP[order.status];
  const isDone = order.status === 'COMPLETED';

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <div className={styles.topBar}>
          <button className={styles.iconBtn} onClick={() => navigate('/')} aria-label="Orqaga">
            <BackIcon />
          </button>
          <div className={styles.topTitle}>Faol buyurtma</div>
          <div className={styles.statusPill}>{statusLabel(order.status)}</div>
        </div>

        <div className={styles.cargoCard}>
          <div className={styles.cargoName}>{order.cargo_name}</div>
          <div className={styles.cargoMeta}>
            <span className={styles.metaChip}><WeightIcon /> {order.weight} t</span>
            {order.total_distance_km != null && (
              <span className={styles.metaChip}>≈ {Math.round(order.total_distance_km)} km</span>
            )}
          </div>
          <div className={styles.priceRow}>
            <span className={styles.priceLabel}>To'lov</span>
            <span className={styles.price}>{formatPrice(order.price)} {order.currency}</span>
          </div>
        </div>

        <div className={styles.sectionTitle}>Marshrut</div>
        <div className={styles.route}>
          {order.waypoints.map((wp, idx) => {
            const isLast = idx === order.waypoints.length - 1;
            return (
              <div key={wp.id} className={styles.checkpoint}>
                <div className={styles.markerCol}>
                  <span className={`${styles.marker} ${styles[`marker_${wp.status}`] ?? ''}`} />
                  {!isLast && <span className={styles.connector} />}
                </div>
                <div className={styles.checkpointBody}>
                  <div className={styles.checkpointType}>{WAYPOINT_TYPE_LABEL[wp.type]}</div>
                  <div className={styles.checkpointAddress}>{wp.address ?? 'Manzil ko’rsatilmagan'}</div>
                  {wp.contact_phone && (
                    <a className={styles.miniCall} href={`tel:${wp.contact_phone}`}>
                      <PhoneIcon size={13} color="var(--color-accent-pressed)" /> {wp.contact_name ?? wp.contact_phone}
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {contact && (
          <>
            <div className={styles.sectionTitle}>Mijoz</div>
            <div className={styles.customerCard}>
              <div className={styles.customerInfo}>
                <div className={styles.customerName}>{contact.contact_name ?? 'Mijoz'}</div>
                <div className={styles.customerPhone}>{contact.contact_phone ?? 'Telefon ko’rsatilmagan'}</div>
              </div>
              {contact.contact_phone && (
                <a className={styles.callBtn} href={`tel:${contact.contact_phone}`} aria-label="Qo'ng'iroq qilish">
                  <PhoneIcon />
                </a>
              )}
            </div>
          </>
        )}

        {error && <div className={styles.errorBanner}>{error}</div>}
      </div>

      <div className={styles.footer}>
        {isDone ? (
          <div className={styles.doneNote}>Buyurtma yakunlandi ✅</div>
        ) : step ? (
          <button className={styles.advanceBtn} onClick={handleAdvance} disabled={updating}>
            {updating ? 'Saqlanmoqda...' : step.label}
          </button>
        ) : (
          <div className={styles.doneNote}>Yuklash vaqti kelishi kutilmoqda</div>
        )}
      </div>
    </div>
  );
}
