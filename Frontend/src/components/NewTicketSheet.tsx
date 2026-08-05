import { useState } from 'react';
import { ApiError } from '../api/client';
import { TICKET_PRIORITY_LABELS, createTicket } from '../api/support';
import type { TicketDetail, TicketPriority } from '../types/api';
import { BottomSheetModal } from './BottomSheetModal';
import styles from './NewTicketSheet.module.css';

// Yangi murojaat (ticket) yaratish formasi — POST /support/tickets.
// Buyurtma sahifasidan chaqirilganda `orderId` oldindan beriladi: shunda support
// xizmati o'sha buyurtmaning holat o'zgarishlarini ticketga avtomatik yozib boradi
// (RabbitMQ `order.*` hodisalari orqali).

const PRIORITIES: TicketPriority[] = ['low', 'normal', 'high', 'urgent'];

// Backend cheklovlari (support_service/schemas.py TicketCreate) — bu yerda ham
// tekshiramizki, foydalanuvchi 422 kutmasdan darhol izoh ko'rsin.
const SUBJECT_MIN = 3;
const BODY_MIN = 5;

interface Props {
  /** Murojaat aniq buyurtmaga tegishli bo'lsa. */
  orderId?: number;
  onClose: () => void;
  onCreated: (ticket: TicketDetail) => void;
}

export function NewTicketSheet({ orderId, onClose, onCreated }: Props) {
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [priority, setPriority] = useState<TicketPriority>('normal');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const valid = subject.trim().length >= SUBJECT_MIN && body.trim().length >= BODY_MIN;

  async function submit() {
    if (!valid || saving) return;
    setSaving(true);
    setError(null);
    try {
      const ticket = await createTicket({
        subject: subject.trim(),
        body: body.trim(),
        order_id: orderId,
        priority,
      });
      onCreated(ticket);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Murojaat yuborilmadi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <BottomSheetModal title="Yangi murojaat" onClose={onClose}>
      <div className={styles.form}>
        {orderId != null && (
          <div className={styles.orderHint}>Buyurtma #{orderId} bo'yicha murojaat</div>
        )}

        {error && <div className={styles.error}>{error}</div>}

        <label className={styles.field}>
          <span className={styles.label}>Mavzu</span>
          <input
            className={styles.input}
            value={subject}
            maxLength={200}
            placeholder="Masalan: Haydovchi kelmadi"
            onChange={(e) => setSubject(e.target.value)}
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>Muammoni tasvirlab bering</span>
          <textarea
            className={styles.textarea}
            value={body}
            maxLength={5000}
            rows={5}
            placeholder="Nima bo'ldi, qachon va qaysi buyurtmada?"
            onChange={(e) => setBody(e.target.value)}
          />
        </label>

        <div className={styles.field}>
          <span className={styles.label}>Muhimlik darajasi</span>
          <div className={styles.priorityRow}>
            {PRIORITIES.map((p) => (
              <button
                key={p}
                type="button"
                className={p === priority ? styles.priorityActive : styles.priority}
                onClick={() => setPriority(p)}
              >
                {TICKET_PRIORITY_LABELS[p]}
              </button>
            ))}
          </div>
        </div>

        <button className={styles.submit} disabled={!valid || saving} onClick={submit}>
          {saving ? 'Yuborilmoqda...' : 'Yuborish'}
        </button>
      </div>
    </BottomSheetModal>
  );
}
