import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { getDashboardStats, listAdminOrders } from '../../api/admin';
import type { AdminDashboardStats, Order } from '../../types/api';
import { formatPrice, statusLabel } from '../../utils/format';
import { DataTable, type Column } from '../components/DataTable';
import { KpiCard } from '../components/KpiCard';
import { StatusBadge } from '../components/StatusBadge';
import shared from '../shared.module.css';
import styles from './AdminDashboard.module.css';

const WEEKDAY = ['Ya', 'Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh'];

const STATUS_TONE: Record<string, string> = {
  PENDING: '#F59E0B',
  SCHEDULED: '#3B82F6',
  ACCEPTED: '#16A34A',
  IN_PROGRESS: '#15803D',
  COMPLETED: '#8A93A2',
  CANCELLED: '#D92D20',
};

const ORDER_COLUMNS: Column<Order>[] = [
  { key: 'id', header: 'ID', width: '70px', render: (o) => `#${o.id}` },
  { key: 'cargo_name', header: 'Yuk', render: (o) => o.cargo_name },
  { key: 'driver_id', header: 'Haydovchi', render: (o) => (o.driver_id ? `#${o.driver_id}` : '—') },
  {
    key: 'price',
    header: 'Narx',
    align: 'right',
    render: (o) => `${formatPrice(Number(o.price))} ${o.currency}`,
  },
  { key: 'status', header: 'Holat', render: (o) => <StatusBadge status={o.status} /> },
];

export function AdminDashboard() {
  const [stats, setStats] = useState<AdminDashboardStats | null>(null);
  const [recent, setRecent] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    // allSettled: biror endpoint yiqilsa ham qolganlari ko'rinadi (masalan stats ishlab,
    // buyurtmalar ro'yxati vaqtincha ishlamasa — dashboard butunlay bo'sh qolmaydi).
    // Aylanma endi alohida so'ralmaydi: u stats.revenue_total ichida DB tomonda SUM
    // bilan hisoblanadi (ilgari sahifalangan ro'yxat qo'shilardi va 200 tadan oshgach
    // noto'g'ri natija berardi).
    Promise.allSettled([getDashboardStats(), listAdminOrders({ limit: 8 })])
      .then(([statsRes, recentRes]) => {
        if (cancelled) return;
        if (statsRes.status === 'fulfilled') setStats(statsRes.value);
        if (recentRes.status === 'fulfilled') setRecent(recentRes.value);
        if (statsRes.status === 'rejected') {
          const err = statsRes.reason;
          setError(err instanceof ApiError ? err.message : "Ma'lumot yuklanmadi");
        }
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const week = stats?.orders_last_7_days ?? [];
  const maxDay = Math.max(1, ...week.map((d) => d.count));
  const statusEntries = Object.entries(stats?.orders_by_status ?? {});
  const statusTotal = statusEntries.reduce((s, [, c]) => s + c, 0);

  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <h1 className={shared.pageTitle}>Dashboard</h1>
          <div className={shared.pageSub}>Platforma umumiy ko'rsatkichlari</div>
        </div>
      </div>

      {error && <div className={shared.errorBanner}>{error}</div>}

      {/* KPI kartalar */}
      <div className={styles.kpiRow}>
        <KpiCard label="Bugungi buyurtma" value={stats?.orders_today ?? 0} sub={`Jami: ${stats?.orders_total ?? 0}`} loading={loading} />
        <KpiCard
          label="Faol haydovchi"
          value={stats?.drivers_online ?? 0}
          sub={`Jonli GPS: ${stats?.drivers_live_gps ?? 0}`}
          loading={loading}
        />
        <KpiCard
          label="Aylanma (yakunlangan)"
          value={stats ? formatPrice(Number(stats.revenue_total)) : '—'}
          sub="UZS · jami yakunlangan buyurtmalar"
          accent
          loading={loading}
        />
        <KpiCard
          label="Bekor qilingan"
          value={stats?.orders_by_status?.CANCELLED ?? 0}
          sub={`Jami foydalanuvchi: ${stats?.users_total ?? 0}`}
          loading={loading}
        />
      </div>

      {/* Grafik + holat ulushi */}
      <div className={styles.chartsRow}>
        <div className={styles.chartCard}>
          <div className={styles.cardTitle}>Haftalik buyurtmalar</div>
          {loading ? (
            <div className={styles.chartSkeleton} />
          ) : week.length === 0 ? (
            <div className={styles.emptyBox}>Ma'lumot yo'q</div>
          ) : (
            <div className={styles.chart}>
              {week.map((d) => {
                const day = new Date(d.date);
                return (
                  <div key={d.date} className={styles.barCol}>
                    <div className={styles.barValue}>{d.count}</div>
                    <div className={styles.barTrack}>
                      <div className={styles.bar} style={{ height: `${Math.max(4, (d.count / maxDay) * 100)}%` }} />
                    </div>
                    <div className={styles.barLabel}>{WEEKDAY[day.getDay()]}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className={styles.chartCard}>
          <div className={styles.cardTitle}>Holat bo'yicha</div>
          {loading ? (
            <div className={styles.chartSkeleton} />
          ) : statusEntries.length === 0 ? (
            <div className={styles.emptyBox}>Ma'lumot yo'q</div>
          ) : (
            <div className={styles.statusList}>
              {statusEntries.map(([status, count]) => (
                <div key={status} className={styles.statusRow}>
                  <span className={styles.statusName}>{statusLabel(status)}</span>
                  <div className={styles.statusBarTrack}>
                    <div
                      className={styles.statusBar}
                      style={{
                        width: `${statusTotal ? (count / statusTotal) * 100 : 0}%`,
                        background: STATUS_TONE[status] ?? 'var(--color-gray-400)',
                      }}
                    />
                  </div>
                  <span className={styles.statusCount}>{count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* So'nggi buyurtmalar */}
      <div>
        <div className={styles.sectionTitle}>So'nggi buyurtmalar</div>
        <DataTable
          columns={ORDER_COLUMNS}
          rows={recent}
          rowKey={(o) => o.id}
          loading={loading}
          emptyText="Hali buyurtma yo'q"
        />
      </div>
    </div>
  );
}
