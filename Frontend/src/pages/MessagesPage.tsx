import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { TICKET_STATUS_LABELS, listTickets } from '../api/support';
import type { TicketListItem } from '../types/api';
import { useAuth } from '../auth/AuthProvider';
import { BottomNav } from '../components/BottomNav';
import { DriverBottomNav } from '../components/DriverBottomNav';
import { MessagesNavIcon } from '../components/icons';
import { NewTicketSheet } from '../components/NewTicketSheet';
import styles from './MessagesPage.module.css';

// Murojaatlar (ticket) ro'yxati — support mikroservisidan olinadi (GET /support/tickets).
// Oddiy foydalanuvchi faqat o'zinikini ko'radi, filtr serverda majburlanadi.

/** Buyurtma sahifasidan "Muammo bormi?" bilan kelinganda shu ekran darhol yangi
 *  murojaat formasini ochadi va buyurtma raqamini oldindan to'ldiradi. */
interface MessagesNavState {
  newTicketForOrderId?: number;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('uz-UZ');
}

export function MessagesPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { role } = useAuth();
  const prefillOrderId = (location.state as MessagesNavState | null)?.newTicketForOrderId;

  // Bu ekran ikkala ilovada ham (sender va haydovchi) ishlatiladi, pastki menyu esa
  // ularda har xil — shuning uchun rolga qarab tanlanadi.
  const Nav = role === 'driver' ? DriverBottomNav : BottomNav;

  const [tickets, setTickets] = useState<TicketListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sheetOpen, setSheetOpen] = useState(prefillOrderId != null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setTickets(await listTickets({ limit: 100 }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Murojaatlar yuklanmadi');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className={styles.page}>
      <div className={styles.topBar}>
        <div className={styles.title}>Xabarlar</div>
        <button className={styles.newBtn} onClick={() => setSheetOpen(true)}>
          Yangi murojaat
        </button>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      {loading ? (
        <div className={styles.list}>
          <div className={styles.skeleton} />
          <div className={styles.skeleton} />
          <div className={styles.skeleton} />
        </div>
      ) : tickets.length === 0 ? (
        <div className={styles.empty}>
          <MessagesNavIcon size={40} color="var(--color-gray-300)" strokeWidth={1.5} />
          <div className={styles.emptyTitle}>Murojaatlar yo'q</div>
          <div className={styles.emptyHint}>
            Savol yoki muammo bo'lsa, "Yangi murojaat" tugmasi orqali yozing — javobni shu
            yerda olasiz
          </div>
        </div>
      ) : (
        <div className={styles.list}>
          {tickets.map((ticket) => (
            <button
              key={ticket.id}
              className={styles.card}
              onClick={() => navigate(`/messages/${ticket.id}`)}
            >
              <div className={styles.cardTop}>
                <span className={styles.subject}>{ticket.subject}</span>
                <span className={`${styles.badge} ${styles[`status_${ticket.status}`]}`}>
                  {TICKET_STATUS_LABELS[ticket.status]}
                </span>
              </div>
              <div className={styles.cardMeta}>
                <span>#{ticket.id}</span>
                {ticket.order_id != null && <span>Buyurtma #{ticket.order_id}</span>}
                <span>{formatDate(ticket.updated_at)}</span>
              </div>
            </button>
          ))}
        </div>
      )}

      {sheetOpen && (
        <NewTicketSheet
          orderId={prefillOrderId}
          onClose={() => setSheetOpen(false)}
          onCreated={(ticket) => {
            setSheetOpen(false);
            navigate(`/messages/${ticket.id}`);
          }}
        />
      )}

      <Nav />
    </div>
  );
}
