import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { listAdminOrders } from '../../api/admin';
import type { Order, OrderStatus } from '../../types/api';
import { formatPrice } from '../../utils/format';
import { AssignDriverModal } from '../components/AssignDriverModal';
import { DataTable, type Column } from '../components/DataTable';
import { OrderEditModal } from '../components/OrderEditModal';
import { Pagination } from '../components/Pagination';
import { StatusBadge } from '../components/StatusBadge';
import shared from '../shared.module.css';
import styles from './AdminOrders.module.css';

const PAGE_SIZE = 20;

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Barcha holatlar' },
  { value: 'PENDING', label: 'Qidirilmoqda' },
  { value: 'SCHEDULED', label: 'Rejalashtirilgan' },
  { value: 'ACCEPTED', label: 'Qabul qilindi' },
  { value: 'IN_PROGRESS', label: "Yo'lda" },
  { value: 'COMPLETED', label: 'Yakunlandi' },
  { value: 'CANCELLED', label: 'Bekor qilindi' },
];

function routeOf(order: Order): string {
  const wps = order.waypoints ?? [];
  if (wps.length === 0) return '—';
  const from = wps[0]?.address ?? '?';
  const to = wps[wps.length - 1]?.address ?? '?';
  return `${from} → ${to}`;
}

export function AdminOrders() {
  const [status, setStatus] = useState('');
  const [skip, setSkip] = useState(0);
  const [rows, setRows] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editTarget, setEditTarget] = useState<Order | null>(null);
  const [assignTarget, setAssignTarget] = useState<Order | null>(null);
  // Biriktirilgandan keyin ro'yxatni qayta yuklash uchun (re-fetch)
  const [reloadKey, setReloadKey] = useState(0);

  const columns: Column<Order>[] = [
    { key: 'id', header: 'ID', width: '70px', render: (o) => `#${o.id}` },
    { key: 'route', header: "Yo'nalish", render: (o) => <span title={routeOf(o)}>{routeOf(o)}</span> },
    { key: 'cargo_name', header: 'Yuk', render: (o) => o.cargo_name },
    { key: 'driver_id', header: 'Haydovchi', render: (o) => (o.driver_id ? `#${o.driver_id}` : '—') },
    {
      key: 'price',
      header: 'Narx',
      align: 'right',
      render: (o) => `${formatPrice(Number(o.price))} ${o.currency}`,
    },
    { key: 'status', header: 'Holat', render: (o) => <StatusBadge status={o.status as OrderStatus} /> },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (o) => (
        <div className={styles.actions}>
          {/* Yakunlangan/bekor qilingan buyurtmaga haydovchi biriktirilmaydi (backend 409) */}
          {o.driver_id == null && o.status !== 'COMPLETED' && o.status !== 'CANCELLED' && (
            <button className={styles.assignBtn} onClick={() => setAssignTarget(o)}>
              Haydovchi biriktirish
            </button>
          )}
          <button className={styles.editBtn} onClick={() => setEditTarget(o)}>
            Tahrirlash
          </button>
        </div>
      ),
    },
  ];

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listAdminOrders({ status: status || undefined, skip, limit: PAGE_SIZE })
      .then((data) => !cancelled && setRows(data))
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : 'Buyurtmalar yuklanmadi');
        setRows([]);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [status, skip, reloadKey]);

  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <h1 className={shared.pageTitle}>Buyurtmalar</h1>
          <div className={shared.pageSub}>Barcha buyurtmalar va ularning holati</div>
        </div>
      </div>

      <div className={shared.toolbar}>
        <select
          className={shared.select}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setSkip(0);
          }}
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(o) => o.id}
          loading={loading}
          error={error}
          emptyText="Buyurtma topilmadi"
        />
        <Pagination skip={skip} limit={PAGE_SIZE} count={rows.length} onChange={setSkip} />
      </div>

      {assignTarget && (
        <AssignDriverModal
          order={assignTarget}
          onClose={() => setAssignTarget(null)}
          onAssigned={() => setReloadKey((k) => k + 1)}
        />
      )}

      {editTarget && (
        <OrderEditModal
          order={editTarget}
          onClose={() => setEditTarget(null)}
          onSaved={(updated) =>
            setRows((prev) => prev.map((o) => (o.id === updated.id ? { ...o, ...updated } : o)))
          }
        />
      )}
    </div>
  );
}
