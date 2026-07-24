import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { listUsers, updateUser } from '../../api/admin';
import type { AdminUserListItem } from '../../types/api';
import { DataTable, type Column } from '../components/DataTable';
import { Pagination } from '../components/Pagination';
import { SearchIconAdmin } from '../icons';
import shared from '../shared.module.css';
import styles from './AdminUsers.module.css';

const PAGE_SIZE = 20;

const ROLE_LABEL: Record<string, string> = {
  admin: 'Admin',
  sender: 'Yuk beruvchi',
  driver: 'Haydovchi',
  guest: 'Mehmon',
  dispatcher: 'Dispetcher',
  manager: 'Menejer',
};

export function AdminUsers() {
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [skip, setSkip] = useState(0);
  const [data, setData] = useState<{ total: number; items: AdminUserListItem[] }>({ total: 0, items: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  // Qidiruvni debounce qilamiz (har harfda so'rov yubormaslik uchun)
  useEffect(() => {
    const t = window.setTimeout(() => {
      setDebounced(search.trim());
      setSkip(0);
    }, 350);
    return () => window.clearTimeout(t);
  }, [search]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listUsers({ search: debounced || undefined, skip, limit: PAGE_SIZE })
      .then((res) => !cancelled && setData(res))
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : 'Foydalanuvchilar yuklanmadi');
        setData({ total: 0, items: [] });
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [debounced, skip]);

  async function toggleBan(user: AdminUserListItem) {
    setBusyId(user.id);
    try {
      const updated = await updateUser(user.id, { is_banned: !user.is_banned });
      setData((prev) => ({
        ...prev,
        items: prev.items.map((u) => (u.id === updated.id ? updated : u)),
      }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "O'zgartirib bo'lmadi");
    } finally {
      setBusyId(null);
    }
  }

  const columns: Column<AdminUserListItem>[] = [
    { key: 'id', header: 'ID', width: '64px', render: (u) => `#${u.id}` },
    {
      key: 'full_name',
      header: 'Foydalanuvchi',
      render: (u) => (
        <div>
          <div className={styles.name}>{u.full_name || '—'}</div>
          {u.username && <div className={styles.username}>@{u.username}</div>}
        </div>
      ),
    },
    { key: 'phone_number', header: 'Telefon', render: (u) => u.phone_number ?? '—' },
    {
      key: 'role',
      header: 'Rol',
      render: (u) => <span className={styles.roleChip}>{ROLE_LABEL[u.role ?? ''] ?? u.role ?? '—'}</span>,
    },
    {
      key: 'status',
      header: 'Holat',
      render: (u) =>
        u.is_banned ? (
          <span className={styles.banned}>Bloklangan</span>
        ) : u.is_active ? (
          <span className={styles.active}>Faol</span>
        ) : (
          <span className={styles.inactive}>Nofaol</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (u) => (
        <button
          className={u.is_banned ? styles.unbanBtn : styles.banBtn}
          disabled={busyId === u.id}
          onClick={() => toggleBan(u)}
        >
          {busyId === u.id ? '...' : u.is_banned ? 'Blokdan chiqarish' : 'Bloklash'}
        </button>
      ),
    },
  ];

  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <h1 className={shared.pageTitle}>Foydalanuvchilar</h1>
          <div className={shared.pageSub}>Jami: {data.total}</div>
        </div>
      </div>

      <div className={shared.toolbar}>
        <div className={shared.searchBox}>
          <SearchIconAdmin />
          <input
            className={shared.searchInput}
            placeholder="Ism, username yoki telefon bo'yicha qidirish"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {error && <div className={shared.errorBanner}>{error}</div>}

      <div>
        <DataTable
          columns={columns}
          rows={data.items}
          rowKey={(u) => u.id}
          loading={loading}
          emptyText="Foydalanuvchi topilmadi"
        />
        <Pagination skip={skip} limit={PAGE_SIZE} count={data.items.length} total={data.total} onChange={setSkip} />
      </div>
    </div>
  );
}
