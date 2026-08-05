import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import {
  TICKET_PRIORITY_LABELS,
  TICKET_STATUS_LABELS,
  getTicket,
  isTicketClosed,
  replyToTicket,
} from '../api/support';
import { useAuth } from '../auth/AuthProvider';
import type { TicketDetail } from '../types/api';
import styles from './TicketPage.module.css';

// Bitta murojaat (ticket) va uning yozishmalari — support mikroservisidan.
// Yozishmada uch xil xabar bo'ladi:
//   1. o'zimniki (author_user_id === userId) — o'ngda, yashil;
//   2. xodim javobi — chapda, oq;
//   3. `is_system: true` — markazda, kulrang. Bularni hech kim yozmaydi: support
//      RabbitMQ'dagi `order.status_changed` / `order.truck_assigned` hodisalarini
//      eshitib, ticketga avtomatik qo'shadi.

function formatTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? ''
    : d.toLocaleString('uz-UZ', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

export function TicketPage() {
  const { ticketId } = useParams<{ ticketId: string }>();
  const navigate = useNavigate();
  const { userId } = useAuth();

  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    if (!ticketId) return;
    try {
      setTicket(await getTicket(Number(ticketId)));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Murojaat yuklanmadi');
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    void load();
  }, [load]);

  // Yangi xabar kelganda oxiriga surish.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [ticket?.messages.length]);

  const closed = ticket != null && isTicketClosed(ticket.status);

  async function send() {
    if (!ticket || !draft.trim() || sending) return;
    setSending(true);
    setError(null);
    try {
      const message = await replyToTicket(ticket.id, draft.trim());
      // Butun ticketni qayta so'ramaymiz — server faqat yangi xabarni qaytaradi.
      setTicket({ ...ticket, messages: [...ticket.messages, message] });
      setDraft('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Xabar yuborilmadi');
      // 409 — ticket shu orada yopilgan bo'lishi mumkin; holatni yangilab olamiz.
      if (err instanceof ApiError && err.status === 409) void load();
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.centered}>
          <div className={styles.spinner} />
        </div>
      </div>
    );
  }

  if (!ticket) {
    return (
      <div className={styles.page}>
        <div className={styles.centered}>
          <div className={styles.errorText}>{error ?? 'Murojaat topilmadi'}</div>
          <button className={styles.backLink} onClick={() => navigate('/messages')}>
            Murojaatlarga qaytish
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.topBar}>
        <button className={styles.backBtn} onClick={() => navigate('/messages')} aria-label="Orqaga">
          ←
        </button>
        <div className={styles.headText}>
          <div className={styles.subject}>{ticket.subject}</div>
          <div className={styles.meta}>
            #{ticket.id} · {TICKET_STATUS_LABELS[ticket.status]} ·{' '}
            {TICKET_PRIORITY_LABELS[ticket.priority]}
            {ticket.order_id != null && ` · Buyurtma #${ticket.order_id}`}
          </div>
        </div>
      </div>

      <div className={styles.thread}>
        {/* Murojaatning asosiy matni — birinchi xabar sifatida ko'rsatiladi */}
        <div className={styles.mine}>
          <div className={styles.bubble}>{ticket.body}</div>
          <div className={styles.time}>{formatTime(ticket.created_at)}</div>
        </div>

        {ticket.messages.map((message) => {
          if (message.is_system) {
            return (
              <div key={message.id} className={styles.system}>
                <span className={styles.systemBubble}>{message.body}</span>
              </div>
            );
          }
          const own = userId != null && message.author_user_id === userId;
          return (
            <div key={message.id} className={own ? styles.mine : styles.theirs}>
              {!own && message.author_role && (
                <div className={styles.author}>Yordam xizmati</div>
              )}
              <div className={styles.bubble}>{message.body}</div>
              <div className={styles.time}>{formatTime(message.created_at)}</div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {closed ? (
        <div className={styles.closedBar}>
          Murojaat yopilgan — yangi xabar yozib bo'lmaydi. Savol qolgan bo'lsa yangi murojaat
          oching.
        </div>
      ) : (
        <div className={styles.composer}>
          <textarea
            className={styles.input}
            value={draft}
            rows={1}
            maxLength={5000}
            placeholder="Xabar yozing..."
            onChange={(e) => setDraft(e.target.value)}
          />
          <button
            className={styles.sendBtn}
            disabled={!draft.trim() || sending}
            onClick={send}
            aria-label="Yuborish"
          >
            {sending ? '...' : '↑'}
          </button>
        </div>
      )}
    </div>
  );
}
