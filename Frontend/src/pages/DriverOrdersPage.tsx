import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { listMyOrders } from '../api/orders';
import { DriverBottomNav } from '../components/DriverBottomNav';
import { ChevronRightIcon } from '../components/icons';
import type { OrderListItem, OrderStatus } from '../types/api';
import { formatPrice, formatRelativeDate, statusLabel } from '../utils/format';
import styles from './DriverOrdersPage.module.css';

const ACTIVE_STATUSES = new Set<OrderStatus>(['SCHEDULED', 'ACCEPTED', 'IN_PROGRESS']);

function statusClass(status: OrderStatus): string {
  if (ACTIVE_STATUSES.has(status)) return styles.chipActive;
  if (status === 'COMPLETED') return styles.chipDone;
  if (status === 'CANCELLED') return styles.chipCancelled;
  return styles.chipNeutral;
}

export function DriverOrdersPage() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<OrderListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMyOrders()
      .then(setOrders)
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : 'Buyurtmalar yuklanmadi');
        setOrders([]);
      });
  }, []);

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <div className={styles.title}>Buyurtmalar</div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        {orders === null && <div className={styles.spinner} />}

        {orders && orders.length === 0 && !error && (
          <div className={styles.empty}>
            <div className={styles.emptyTitle}>Hali buyurtma yo'q</div>
            <div className={styles.emptyHint}>Liniyaga chiqib birinchi taklifni qabul qiling.</div>
          </div>
        )}

        <div className={styles.list}>
          {orders?.map((order) => (
            <button key={order.id} className={styles.row} onClick={() => navigate(`/active/${order.id}`)}>
              <div className={styles.rowMain}>
                <div className={styles.rowTop}>
                  <span className={styles.cargo}>{order.cargo_name}</span>
                  <span className={statusClass(order.status)}>{statusLabel(order.status)}</span>
                </div>
                <div className={styles.rowMeta}>
                  {formatRelativeDate(order.created_at)} · {order.weight} t
                </div>
              </div>
              <div className={styles.rowRight}>
                <span className={styles.price}>{formatPrice(order.price)} {order.currency}</span>
                <ChevronRightIcon />
              </div>
            </button>
          ))}
        </div>
      </div>

      <DriverBottomNav />
    </div>
  );
}
