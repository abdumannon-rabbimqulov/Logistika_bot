import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import {
  TICKET_PRIORITY_LABELS,
  TICKET_STATUS_LABELS,
  getTicket,
  isTicketClosed,
  listTickets,
  replyToTicket,
  updateTicketStatus,
} from '../../api/support';
import type { TicketDetail, TicketListItem, TicketStatus } from '../../types/api';
import { DataTable } from '../components/DataTable';
import type { Column } from '../components/DataTable';
import { Modal } from '../components/Modal';
import { useToast } from '../components/Toast';
import shared from '../shared.module.css';
import styles from './AdminTickets.module.css';

// Foydalanuvchilarning murojaatlari — support MIKROSERVISIDAN keladi (`/support/...`,
// `/api` ostida emas). Xodim (admin/manager) hamma murojaatni ko'radi va holatini
// o'zgartira oladi; oddiy foydalanuvchi esa faqat o'zinikini.

const PAGE_SIZE = 50;

const STATUSES: TicketStatus[] = ['open', 'in_progress', 'resolved', 'closed'];

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('uz-UZ');
}

export function AdminTickets() {
  const toast = useToast();

  const [rows, setRows] = useState<TicketListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<TicketStatus | ''>('');
  const [page, setPage] = useState(0);

  const [active, setActive] = useState<TicketDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [reply, setReply] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRows(
        await listTickets({
          status: statusFilter || undefined,
          limit: PAGE_SIZE,
          offset: page * PAGE_SIZE,
        }),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Murojaatlar yuklanmadi');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function openTicket(row: TicketListItem) {
    setDetailLoading(true);
    setReply('');
    try {
      setActive(await getTicket(row.id));
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Murojaat ochilmadi');
    } finally {
      setDetailLoading(false);
    }
  }

  async function sendReply() {
    if (!active || !reply.trim() || busy) return;
    setBusy(true);
    try {
      const message = await replyToTicket(active.id, reply.trim());
      setActive({ ...active, messages: [...active.messages, message] });
      setReply('');
      toast.success('Javob yuborildi');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'Javob yuborilmadi');
    } finally {
      setBusy(false);
    }
  }

  async function changeStatus(status: TicketStatus) {
    if (!active || busy) return;
    setBusy(true);
    try {
      const updated = await updateTicketStatus(active.id, status);
      // Server faqat ticketni qaytaradi (yozishmalarsiz emas — TicketDetail), lekin
      // ro'yxatni ham yangilab qo'yamiz, aks holda jadvalda eski holat qolardi.
      setActive(updated);
      setRows((prev) => prev.map((r) => (r.id === updated.id ? { ...r, status: updated.status } : r)));
      toast.success('Holat yangilandi');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Holat o'zgartirilmadi");
    } finally {
      setBusy(false);
    }
  }

  const columns: Column<TicketListItem>[] = [
    { key: 'id', header: 'ID', width: '70px', render: (r) => `#${r.id}` },
    { key: 'subject', header: 'Mavzu' },
    {
      key: 'user',
      header: 'Foydalanuvchi',
      render: (r) => `${r.user_id}${r.user_role ? ` (${r.user_role})` : ''}`,
    },
    {
      key: 'order_id',
      header: 'Buyurtma',
      render: (r) => (r.order_id != null ? `#${r.order_id}` : '—'),
    },
    {
      key: 'priority',
      header: 'Muhimlik',
      render: (r) => TICKET_PRIORITY_LABELS[r.priority] ?? r.priority,
    },
    {
      key: 'status',
      header: 'Holat',
      render: (r) => (
        <span className={`${styles.badge} ${styles[`status_${r.status}`]}`}>
          {TICKET_STATUS_LABELS[r.status]}
        </span>
      ),
    },
    { key: 'updated_at', header: "O'zgargan", render: (r) => formatDateTime(r.updated_at) },
  ];

  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <h1 className={shared.pageTitle}>Murojaatlar</h1>
          <div className={shared.pageSub}>
            Foydalanuvchilardan kelgan savol va shikoyatlar (support xizmati)
          </div>
        </div>
      </div>

      <div className={shared.toolbar}>
        <select
          className={shared.select}
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as TicketStatus | '');
            setPage(0);
          }}
        >
          <option value="">Barcha holatlar</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {TICKET_STATUS_LABELS[s]}
            </option>
          ))}
        </select>

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
        rowKey={(r) => r.id}
        loading={loading}
        error={error}
        emptyText="Murojaat yo'q"
        onRowClick={openTicket}
      />

      {(active || detailLoading) && (
        <Modal
          title={active ? `#${active.id} — ${active.subject}` : 'Yuklanmoqda...'}
          onClose={() => setActive(null)}
          footer={
            active && (
              <div className={styles.footer}>
                <select
                  className={shared.select}
                  value={active.status}
                  disabled={busy}
                  onChange={(e) => void changeStatus(e.target.value as TicketStatus)}
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {TICKET_STATUS_LABELS[s]}
                    </option>
                  ))}
                </select>
                <button className={shared.ghostBtn} onClick={() => setActive(null)}>
                  Yopish
                </button>
              </div>
            )
          }
        >
          {detailLoading || !active ? (
            <div className={styles.loadingBox}>Yuklanmoqda...</div>
          ) : (
            <div className={styles.detail}>
              <div className={styles.detailMeta}>
                Foydalanuvchi {active.user_id}
                {active.user_role && ` (${active.user_role})`} ·{' '}
                {TICKET_PRIORITY_LABELS[active.priority]}
                {active.order_id != null && ` · Buyurtma #${active.order_id}`} ·{' '}
                {formatDateTime(active.created_at)}
              </div>

              <div className={styles.thread}>
                <div className={styles.userMsg}>
                  <div className={styles.msgBody}>{active.body}</div>
                  <div className={styles.msgTime}>{formatDateTime(active.created_at)}</div>
                </div>

                {active.messages.map((m) =>
                  m.is_system ? (
                    <div key={m.id} className={styles.systemMsg}>
                      {m.body}
                    </div>
                  ) : (
                    <div
                      key={m.id}
                      className={m.author_user_id === active.user_id ? styles.userMsg : styles.staffMsg}
                    >
                      <div className={styles.msgAuthor}>
                        {m.author_user_id === active.user_id ? 'Foydalanuvchi' : 'Xodim'}
                      </div>
                      <div className={styles.msgBody}>{m.body}</div>
                      <div className={styles.msgTime}>{formatDateTime(m.created_at)}</div>
                    </div>
                  ),
                )}
              </div>

              {isTicketClosed(active.status) ? (
                <div className={styles.closedNote}>
                  Murojaat yopilgan — javob yozish uchun avval holatini "Ochiq" yoki
                  "Ko’rib chiqilmoqda" ga qaytaring.
                </div>
              ) : (
                <div className={styles.replyBox}>
                  <textarea
                    className={styles.replyInput}
                    rows={3}
                    maxLength={5000}
                    value={reply}
                    placeholder="Javob yozing..."
                    onChange={(e) => setReply(e.target.value)}
                  />
                  <button
                    className={shared.primaryBtn}
                    disabled={!reply.trim() || busy}
                    onClick={sendReply}
                  >
                    {busy ? 'Yuborilmoqda...' : 'Javob yuborish'}
                  </button>
                </div>
              )}
            </div>
          )}
        </Modal>
      )}
    </div>
  );
}
