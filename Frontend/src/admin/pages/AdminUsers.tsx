import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { deactivateUser, listUsers, updateUser } from '../../api/admin';
import type { AdminUserListItem } from '../../types/api';
import { BalanceModal } from '../components/BalanceModal';
import { DataTable, type Column } from '../components/DataTable';
import { Modal } from '../components/Modal';
import { Pagination } from '../components/Pagination';
import { UserEditModal } from '../components/UserEditModal';
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
  const [editTarget, setEditTarget] = useState<AdminUserListItem | null>(null);
  const [balanceTarget, setBalanceTarget] = useState<AdminUserListItem | null>(null);
  const [deactivateTarget, setDeactivateTarget] = useState<AdminUserListItem | null>(null);

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

  function applyUpdated(updated: AdminUserListItem) {
    setData((prev) => ({
      ...prev,
      items: prev.items.map((u) => (u.id === updated.id ? updated : u)),
    }));
  }

  async function toggleBan(user: AdminUserListItem) {
    setBusyId(user.id);
    try {
      applyUpdated(await updateUser(user.id, { is_banned: !user.is_banned }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "O'zgartirib bo'lmadi");
    } finally {
      setBusyId(null);
    }
  }

  async function confirmDeactivate() {
    if (!deactivateTarget) return;
    setBusyId(deactivateTarget.id);
    setError(null);
    try {
      await deactivateUser(deactivateTarget.id);
      // 204 — javob tanasi yo'q, shuning uchun qatorni lokal yangilaymiz
      applyUpdated({ ...deactivateTarget, is_active: false });
      setDeactivateTarget(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Nofaol qilib bo'lmadi");
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
      key: 'balance',
      header: 'Balans',
      render: (u) => (
        <span className={Number(u.balance) < 0 ? styles.debt : undefined}>
          {new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 0 }).format(Number(u.balance))} UZS
        </span>
      ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (u) => (
        <div className={styles.actions}>
          <button className={styles.ghostAction} onClick={() => setEditTarget(u)}>
            Tahrirlash
          </button>
          <button className={styles.ghostAction} onClick={() => setBalanceTarget(u)}>
            Balans
          </button>
          <button
            className={u.is_banned ? styles.unbanBtn : styles.banBtn}
            disabled={busyId === u.id}
            onClick={() => toggleBan(u)}
          >
            {busyId === u.id ? '...' : u.is_banned ? 'Blokdan chiqarish' : 'Bloklash'}
          </button>
          {u.is_active && (
            <button className={styles.banBtn} onClick={() => setDeactivateTarget(u)}>
              Nofaol qilish
            </button>
          )}
        </div>
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

      {editTarget && (
        <UserEditModal user={editTarget} onClose={() => setEditTarget(null)} onSaved={applyUpdated} />
      )}

      {balanceTarget && (
        <BalanceModal
          userId={balanceTarget.id}
          userName={balanceTarget.full_name || `Foydalanuvchi #${balanceTarget.id}`}
          initialBalance={Number(balanceTarget.balance)}
          onClose={() => setBalanceTarget(null)}
          onChanged={(newBalance) => applyUpdated({ ...balanceTarget, balance: newBalance })}
        />
      )}

      {deactivateTarget && (
        <Modal
          title="Akkauntni nofaol qilish"
          onClose={() => setDeactivateTarget(null)}
          footer={
            <>
              <button className={shared.ghostBtn} onClick={() => setDeactivateTarget(null)}>
                Bekor qilish
              </button>
              <button
                className={styles.dangerBtn}
                disabled={busyId === deactivateTarget.id}
                onClick={confirmDeactivate}
              >
                {busyId === deactivateTarget.id ? '...' : 'Nofaol qilish'}
              </button>
            </>
          }
        >
          <div className={styles.confirmText}>
            <strong>{deactivateTarget.full_name || `#${deactivateTarget.id}`}</strong> akkaunti nofaol
            qilinadi — u tizimga kira olmaydi. Ma’lumotlari o‘chirilmaydi, keyin “Tahrirlash” orqali
            qayta faollashtirish mumkin.
          </div>
        </Modal>
      )}
    </div>
  );
}
