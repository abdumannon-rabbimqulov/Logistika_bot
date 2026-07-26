import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { blockDriver, listDrivers, unblockDriver } from '../../api/admin';
import type { AdminDriverListItem } from '../../types/api';
import { DataTable, type Column } from '../components/DataTable';
import { Modal } from '../components/Modal';
import { Pagination } from '../components/Pagination';
import { SearchIconAdmin } from '../icons';
import shared from '../shared.module.css';
import styles from './DriverBlocksPanel.module.css';

const PAGE_SIZE = 20;

function formatMoney(value: number): string {
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 0 }).format(value);
}

/** Haydovchilar ro'yxati: balans, qarz tufayli avtomatik blok va uni ochish. */
export function DriverBlocksPanel() {
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [onlyBlocked, setOnlyBlocked] = useState(false);
  const [skip, setSkip] = useState(0);
  const [data, setData] = useState<{ total: number; items: AdminDriverListItem[] }>({ total: 0, items: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  // Modal holati: blokdan chiqarish (ixtiyoriy balans to'ldirish bilan) yoki bloklash
  const [unblockTarget, setUnblockTarget] = useState<AdminDriverListItem | null>(null);
  const [topUp, setTopUp] = useState('');
  const [note, setNote] = useState('');
  const [blockTarget, setBlockTarget] = useState<AdminDriverListItem | null>(null);
  const [blockReason, setBlockReason] = useState('');

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
    listDrivers({
      search: debounced || undefined,
      is_blocked: onlyBlocked ? true : undefined,
      skip,
      limit: PAGE_SIZE,
    })
      .then((res) => !cancelled && setData(res))
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : 'Haydovchilar yuklanmadi');
        setData({ total: 0, items: [] });
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [debounced, onlyBlocked, skip]);

  function applyUpdated(updated: AdminDriverListItem) {
    setData((prev) => ({
      ...prev,
      // "Faqat bloklanganlar" filtri yoqilgan bo'lsa, ochilgan haydovchi ro'yxatdan chiqadi
      items:
        onlyBlocked && !updated.is_blocked
          ? prev.items.filter((d) => d.driver_id !== updated.driver_id)
          : prev.items.map((d) => (d.driver_id === updated.driver_id ? updated : d)),
      total: onlyBlocked && !updated.is_blocked ? Math.max(0, prev.total - 1) : prev.total,
    }));
  }

  async function submitUnblock() {
    if (!unblockTarget) return;
    const amount = topUp.trim() ? Number(topUp.replace(/\s/g, '')) : undefined;
    if (amount !== undefined && (!Number.isFinite(amount) || amount <= 0)) {
      setError("To'ldirish summasi musbat son bo'lishi kerak");
      return;
    }
    setBusyId(unblockTarget.driver_id);
    setError(null);
    try {
      const updated = await unblockDriver(unblockTarget.driver_id, {
        top_up_amount: amount,
        note: note.trim() || undefined,
      });
      applyUpdated(updated);
      setUnblockTarget(null);
      setTopUp('');
      setNote('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Blokdan chiqarib bo'lmadi");
    } finally {
      setBusyId(null);
    }
  }

  async function submitBlock() {
    if (!blockTarget || blockReason.trim().length < 3) return;
    setBusyId(blockTarget.driver_id);
    setError(null);
    try {
      const updated = await blockDriver(blockTarget.driver_id, blockReason.trim());
      applyUpdated(updated);
      setBlockTarget(null);
      setBlockReason('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Bloklab bo'lmadi");
    } finally {
      setBusyId(null);
    }
  }

  const columns: Column<AdminDriverListItem>[] = [
    {
      key: 'driver',
      header: 'Haydovchi',
      render: (d) => (
        <div>
          <div className={styles.name}>{d.full_name ?? `Haydovchi #${d.driver_id}`}</div>
          <div className={styles.sub}>
            #{d.driver_id} · {d.phone_number ?? '—'}
          </div>
        </div>
      ),
    },
    { key: 'truck_number', header: 'Davlat raqami', render: (d) => d.truck_number },
    {
      key: 'balance',
      header: 'Balans',
      render: (d) => (
        <span className={d.balance < 0 ? styles.debt : styles.balanceOk}>
          {formatMoney(d.balance)} UZS
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Holat',
      render: (d) =>
        d.is_blocked ? (
          <div>
            <span className={styles.blocked}>
              {d.blocked_for_debt ? 'Qarz uchun bloklangan' : 'Bloklangan'}
            </span>
            {d.block_reason && <div className={styles.reason}>{d.block_reason}</div>}
          </div>
        ) : (
          <span className={styles.active}>{d.is_available ? 'Liniyada' : 'Faol (liniyada emas)'}</span>
        ),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (d) =>
        d.is_blocked ? (
          <button
            className={styles.unblockBtn}
            disabled={busyId === d.driver_id}
            onClick={() => {
              setUnblockTarget(d);
              setTopUp(d.balance < 0 ? String(Math.abs(d.balance)) : '');
              setNote('');
            }}
          >
            {busyId === d.driver_id ? '...' : 'Blokdan chiqarish'}
          </button>
        ) : (
          <button
            className={styles.blockBtn}
            disabled={busyId === d.driver_id}
            onClick={() => {
              setBlockTarget(d);
              setBlockReason('');
            }}
          >
            Bloklash
          </button>
        ),
    },
  ];

  return (
    <div>
      <div className={shared.toolbar}>
        <div className={shared.searchBox}>
          <SearchIconAdmin />
          <input
            className={shared.searchInput}
            placeholder="Ism, telefon yoki davlat raqami"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <label className={styles.filterToggle}>
          <input
            type="checkbox"
            checked={onlyBlocked}
            onChange={(e) => {
              setOnlyBlocked(e.target.checked);
              setSkip(0);
            }}
          />
          Faqat bloklanganlar
        </label>
      </div>

      {error && <div className={shared.errorBanner}>{error}</div>}

      <DataTable
        columns={columns}
        rows={data.items}
        rowKey={(d) => d.driver_id}
        loading={loading}
        emptyText={onlyBlocked ? 'Bloklangan haydovchi yo‘q' : 'Haydovchi topilmadi'}
      />
      <Pagination skip={skip} limit={PAGE_SIZE} count={data.items.length} total={data.total} onChange={setSkip} />

      {unblockTarget && (
        <Modal
          title={`${unblockTarget.full_name ?? `Haydovchi #${unblockTarget.driver_id}`} — blokdan chiqarish`}
          onClose={() => setUnblockTarget(null)}
          footer={
            <>
              <button className={shared.ghostBtn} onClick={() => setUnblockTarget(null)}>
                Bekor qilish
              </button>
              <button
                className={shared.primaryBtn}
                disabled={busyId === unblockTarget.driver_id}
                onClick={submitUnblock}
              >
                {busyId === unblockTarget.driver_id ? 'Bajarilmoqda...' : 'Ochib berish'}
              </button>
            </>
          }
        >
          <div className={styles.modalBody}>
            <div className={styles.balanceRow}>
              <span>Joriy balans</span>
              <strong className={unblockTarget.balance < 0 ? styles.debt : styles.balanceOk}>
                {formatMoney(unblockTarget.balance)} UZS
              </strong>
            </div>

            {unblockTarget.balance < 0 && (
              <div className={styles.warning}>
                Balans manfiy. Qarz yopilmasa, keyingi yakunlangan buyurtma komissiyasi
                yechilganda haydovchi yana avtomatik bloklanadi.
              </div>
            )}

            <label className={styles.field}>
              <span className={styles.label}>Balansga qo‘shish (ixtiyoriy)</span>
              <input
                className={styles.input}
                inputMode="numeric"
                placeholder="0"
                value={topUp}
                onChange={(e) => setTopUp(e.target.value)}
              />
            </label>

            <label className={styles.field}>
              <span className={styles.label}>Izoh (balans tarixiga yoziladi)</span>
              <input
                className={styles.input}
                placeholder="Masalan: qarz naqd to‘landi"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </label>
          </div>
        </Modal>
      )}

      {blockTarget && (
        <Modal
          title={`${blockTarget.full_name ?? `Haydovchi #${blockTarget.driver_id}`} — bloklash`}
          onClose={() => setBlockTarget(null)}
          footer={
            <>
              <button className={shared.ghostBtn} onClick={() => setBlockTarget(null)}>
                Bekor qilish
              </button>
              <button
                className={styles.blockConfirmBtn}
                disabled={blockReason.trim().length < 3 || busyId === blockTarget.driver_id}
                onClick={submitBlock}
              >
                {busyId === blockTarget.driver_id ? 'Bajarilmoqda...' : 'Bloklash'}
              </button>
            </>
          }
        >
          <div className={styles.modalBody}>
            <label className={styles.field}>
              <span className={styles.label}>Sabab (haydovchiga ko‘rsatiladi)</span>
              <input
                className={styles.input}
                placeholder="Kamida 3 ta belgi"
                value={blockReason}
                onChange={(e) => setBlockReason(e.target.value)}
              />
            </label>
            <div className={styles.warning}>
              Bloklangan haydovchi liniyaga chiqa olmaydi va buyurtma qabul qila olmaydi.
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
