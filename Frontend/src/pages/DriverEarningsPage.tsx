import { useEffect, useMemo, useState } from 'react';
import { ApiError } from '../api/client';
import { listMyOrders } from '../api/orders';
import { DriverBottomNav } from '../components/DriverBottomNav';
import { StarIcon } from '../components/icons';
import type { OrderListItem } from '../types/api';
import { formatPrice } from '../utils/format';
import { useDriverCabinet } from './DriverCabinetContext';
import styles from './DriverEarningsPage.module.css';

const DAY_LABELS = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']; // Dushanba..Yakshanba

interface DayBucket {
  label: string;
  total: number;
}

// Oxirgi 7 kunni (bugundan orqaga) Dushanba-boshli hafta indeksiga joylaydi.
function buildWeek(completed: OrderListItem[]): { buckets: DayBucket[]; weekTotal: number; weekCount: number } {
  const now = new Date();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  start.setDate(start.getDate() - 6); // 7 kunlik oyna (bugun + oldingi 6 kun)

  const buckets: DayBucket[] = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    const weekday = (d.getDay() + 6) % 7; // 0=Dushanba
    return { label: DAY_LABELS[weekday], total: 0 };
  });

  let weekTotal = 0;
  let weekCount = 0;
  for (const order of completed) {
    const created = new Date(order.created_at);
    const dayIndex = Math.floor((created.getTime() - start.getTime()) / 86_400_000);
    if (dayIndex >= 0 && dayIndex < 7) {
      buckets[dayIndex].total += Number(order.price);
      weekTotal += Number(order.price);
      weekCount += 1;
    }
  }
  return { buckets, weekTotal, weekCount };
}

export function DriverEarningsPage() {
  const { cabinet } = useDriverCabinet();
  const [orders, setOrders] = useState<OrderListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMyOrders()
      .then(setOrders)
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : 'Ma’lumot yuklanmadi');
        setOrders([]);
      });
  }, []);

  const completed = useMemo(() => (orders ?? []).filter((o) => o.status === 'COMPLETED'), [orders]);
  const { buckets, weekTotal, weekCount } = useMemo(() => buildWeek(completed), [completed]);
  const maxBucket = Math.max(1, ...buckets.map((b) => b.total));
  const recent = completed.slice(0, 8);

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <div className={styles.title}>Daromad</div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        {/* Haftalik daromad grafigi (qora karta, yashil ustunlar) */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeaderLabel}>Shu hafta</div>
          <div className={styles.chartTotal}>
            {formatPrice(weekTotal)} <span className={styles.chartCurrency}>{cabinet.currency}</span>
          </div>
          <div className={styles.chart}>
            {buckets.map((b, i) => (
              <div key={i} className={styles.barCol}>
                <div className={styles.barTrack}>
                  <div
                    className={styles.bar}
                    style={{ height: `${Math.max(4, (b.total / maxBucket) * 100)}%` }}
                  />
                </div>
                <span className={styles.barLabel}>{b.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Statistika plitkalari */}
        <div className={styles.statsRow}>
          <div className={styles.statTile}>
            <div className={styles.statValue}>{weekCount}</div>
            <div className={styles.statLabel}>Shu hafta safar</div>
          </div>
          <div className={styles.statTile}>
            <div className={styles.statValue}>{completed.length}</div>
            <div className={styles.statLabel}>Jami yakunlangan</div>
          </div>
          <div className={styles.statTile}>
            <div className={styles.statValueRating}>
              <StarIcon size={15} /> {cabinet.rating.toFixed(1)}
            </div>
            <div className={styles.statLabel}>O'rtacha reyting</div>
          </div>
        </div>

        {/* Oxirgi to'lovlar */}
        <div className={styles.sectionTitle}>Oxirgi to'lovlar</div>
        {orders === null ? (
          <div className={styles.spinner} />
        ) : recent.length === 0 ? (
          <div className={styles.empty}>Hali yakunlangan buyurtma yo'q</div>
        ) : (
          <div className={styles.payList}>
            {recent.map((order) => (
              <div key={order.id} className={styles.payRow}>
                <div className={styles.payIcon}>+</div>
                <div className={styles.payInfo}>
                  <div className={styles.payCargo}>{order.cargo_name}</div>
                  <div className={styles.payDate}>
                    {new Date(order.created_at).toLocaleDateString('uz-UZ', { day: 'numeric', month: 'long' })}
                  </div>
                </div>
                <div className={styles.payAmount}>+{formatPrice(order.price)} {order.currency}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <DriverBottomNav />
    </div>
  );
}
