import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { listAvailableOrders, listMyOrders } from '../api/orders';
import { DriverBottomNav } from '../components/DriverBottomNav';
import { ChevronRightIcon } from '../components/icons';
import type { OrderListItem, OrderStatus } from '../types/api';
import { formatPrice, formatRelativeDate, statusLabel } from '../utils/format';
import styles from './DriverOrdersPage.module.css';

const ACTIVE_STATUSES = new Set<OrderStatus>(['SCHEDULED', 'ACCEPTED', 'IN_PROGRESS']);

/** "Mening" — menga biriktirilganlar (GET /orders);
 *  "Mavjud" — hali haydovchisi topilmagan buyurtmalar (GET /orders/available/list). */
type Tab = 'mine' | 'available';

function statusClass(status: OrderStatus): string {
  if (ACTIVE_STATUSES.has(status)) return styles.chipActive;
  if (status === 'COMPLETED') return styles.chipDone;
  if (status === 'CANCELLED') return styles.chipCancelled;
  return styles.chipNeutral;
}

export function DriverOrdersPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>('mine');
  const [orders, setOrders] = useState<OrderListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (which: Tab) => {
    setOrders(null);
    setError(null);
    try {
      setOrders(which === 'mine' ? await listMyOrders() : await listAvailableOrders());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Buyurtmalar yuklanmadi');
      setOrders([]);
    }
  }, []);

  useEffect(() => {
    void load(tab);
  }, [tab, load]);

  const isMine = tab === 'mine';

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <div className={styles.title}>Buyurtmalar</div>

        <div className={styles.tabs}>
          <button className={isMine ? styles.tabActive : styles.tab} onClick={() => setTab('mine')}>
            Mening buyurtmalarim
          </button>
          <button
            className={!isMine ? styles.tabActive : styles.tab}
            onClick={() => setTab('available')}
          >
            Mavjud
          </button>
        </div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        {orders === null && <div className={styles.spinner} />}

        {orders && orders.length === 0 && !error && (
          <div className={styles.empty}>
            <div className={styles.emptyTitle}>
              {isMine ? "Hali buyurtma yo'q" : "Hozircha ochiq buyurtma yo'q"}
            </div>
            <div className={styles.emptyHint}>
              {isMine
                ? 'Liniyaga chiqib birinchi taklifni qabul qiling.'
                : "Yangi buyurtma paydo bo'lganda taklif o'zi keladi."}
            </div>
          </div>
        )}

        {/* Ro'yxatdan to'g'ridan-to'g'ri qabul qilish yo'li ATAYLAB yo'q: navbat va
            60 soniyalik taklif oynasi server tomonida boshqariladi (dispatch), aks
            holda bir buyurtmani bir necha haydovchi bir vaqtda olishga urinardi. */}
        {!isMine && orders != null && orders.length > 0 && (
          <div className={styles.availableHint}>
            Bu ro'yxat ma'lumot uchun. Buyurtma sizga navbat bo'yicha taklif sifatida keladi —
            uni bosh sahifada qabul qilasiz.
          </div>
        )}

        <div className={styles.list}>
          {orders?.map((order) => (
            <button
              key={order.id}
              className={styles.row}
              disabled={!isMine}
              onClick={isMine ? () => navigate(`/active/${order.id}`) : undefined}
            >
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
                <span className={styles.price}>
                  {formatPrice(order.price)} {order.currency}
                </span>
                {isMine && <ChevronRightIcon />}
              </div>
            </button>
          ))}
        </div>
      </div>

      <DriverBottomNav />
    </div>
  );
}
