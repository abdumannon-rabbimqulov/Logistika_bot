import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../../api/client';
import { listManagerOrders } from '../../api/manager';
import { DataTable } from '../../admin/components/DataTable';
import type { Column } from '../../admin/components/DataTable';
import { StatusBadge } from '../../admin/components/StatusBadge';
import shared from '../../admin/shared.module.css';
import type { ManagerOrderListItem, OrderStatus } from '../../types/api';
import styles from './ManagerOrders.module.css';

// Menejerning asosiy ish ro'yxati. Narx ustuni ATAYLAB yo'q — backend ham uni
// qaytarmaydi (manager/schemas.py).

const PAGE_SIZE = 50;

const STATUSES: OrderStatus[] = [
  'SCHEDULED',
  'PENDING',
  'ACCEPTED',
  'IN_PROGRESS',
  'COMPLETED',
  'CANCELLED',
];

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('uz-UZ');
}

export function ManagerOrders() {
  const navigate = useNavigate();

  const [rows, setRows] = useState<ManagerOrderListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<OrderStatus | ''>('');
  const [unassigned, setUnassigned] = useState(false);
  const [page, setPage] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(
        await listManagerOrders({
          status: status || undefined,
          unassigned: unassigned || undefined,
          limit: PAGE_SIZE,
          offset: page * PAGE_SIZE,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Buyurtmalar yuklanmadi');
    } finally {
      setLoading(false);
    }
  }, [status, unassigned, page]);

  useEffect(() => {
    void load();
  }, [load]);

  const columns: Column<ManagerOrderListItem>[] = [
    { key: 'id', header: 'ID', width: '80px', render: (o) => `#${o.id}` },
    { key: 'cargo_name', header: 'Yuk' },
    { key: 'weight', header: 'Og‘irlik', align: 'right', render: (o) => `${o.weight} t` },
    { key: 'status', header: 'Holat', render: (o) => <StatusBadge status={o.status} /> },
    {
      key: 'driver_id',
      header: 'Haydovchi',
      render: (o) =>
        o.driver_id != null ? (
          `#${o.driver_id}`
        ) : (
          <span className={styles.unassigned}>Biriktirilmagan</span>
        ),
    },
    { key: 'pickup_at', header: 'Yuklash vaqti', render: (o) => formatDateTime(o.pickup_at) },
    {
      key: 'overload_warning',
      header: 'Ogohlantirish',
      render: (o) =>
        o.overload_warning ? <span className={styles.warn}>{o.overload_warning}</span> : '—',
    },
  ];

  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <h1 className={shared.pageTitle}>Buyurtmalar</h1>
          <div className={shared.pageSub}>
            Buyurtmalarni kuzatish, holatini yangilash va mashina biriktirish
          </div>
        </div>
      </div>

      <div className={shared.toolbar}>
        <select
          className={shared.select}
          value={status}
          onChange={(e) => {
            setStatus(e.target.value as OrderStatus | '');
            setPage(0);
          }}
        >
          <option value="">Barcha holatlar</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <label className={styles.checkbox}>
          <input
            type="checkbox"
            checked={unassigned}
            onChange={(e) => {
              setUnassigned(e.target.checked);
              setPage(0);
            }}
          />
          <span>Faqat biriktirilmaganlar</span>
        </label>

        <button
          className={shared.ghostBtn}
          disabled={page === 0}
          onClick={() => setPage((p) => Math.max(0, p - 1))}
        >
          ← Oldingi
        </button>
        <button
          className={shared.ghostBtn}
          disabled={rows.length < PAGE_SIZE}
          onClick={() => setPage((p) => p + 1)}
        >
          Keyingi →
        </button>
      </div>

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(o) => o.id}
        loading={loading}
        error={error}
        emptyText="Buyurtma topilmadi"
        onRowClick={(o) => navigate(`/manager/orders/${o.id}`)}
      />
    </div>
  );
}
