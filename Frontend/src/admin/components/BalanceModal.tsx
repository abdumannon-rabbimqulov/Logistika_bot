import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { adjustUserBalance, listBalanceTransactions } from '../../api/admin';
import type { BalanceTransaction } from '../../types/api';
import { Modal } from './Modal';
import shared from '../shared.module.css';
import styles from './BalanceModal.module.css';

interface Props {
  userId: number;
  userName: string;
  /** Modal ochilgandagi balans (jadvaldan). Amaldan keyin javobdagi qiymat bilan yangilanadi. */
  initialBalance: number;
  onClose: () => void;
  /** Balans o'zgargach chaqiriladi — chaqiruvchi sahifa qatorini yangilashi uchun. */
  onChanged?: (newBalance: number) => void;
}

const TYPE_LABEL: Record<string, string> = {
  ORDER_COMMISSION: 'Komissiya',
  ADMIN_ADJUSTMENT: 'Admin tuzatishi',
};

function formatMoney(value: number): string {
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 2 }).format(value);
}

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('uz-UZ');
}

/** Foydalanuvchi balansi: to'ldirish/yechish (POST .../balance/adjust) + tarix
 *  (GET .../balance/transactions). Har qanday foydalanuvchi uchun mustaqil ishlaydi. */
export function BalanceModal({ userId, userName, initialBalance, onClose, onChanged }: Props) {
  const [balance, setBalance] = useState(initialBalance);
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [sign, setSign] = useState<'plus' | 'minus'>('plus');
  const [items, setItems] = useState<BalanceTransaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadHistory() {
    setLoading(true);
    try {
      setItems(await listBalanceTransactions(userId, { limit: 20 }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Tarix yuklanmadi');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  async function submit() {
    const raw = Number(amount.replace(/\s/g, '').replace(',', '.'));
    if (!Number.isFinite(raw) || raw <= 0) {
      setError("Summa musbat son bo'lishi kerak");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const tx = await adjustUserBalance(userId, sign === 'plus' ? raw : -raw, note.trim() || undefined);
      setBalance(tx.balance_after);
      onChanged?.(tx.balance_after);
      setAmount('');
      setNote('');
      await loadHistory();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Balansni o'zgartirib bo'lmadi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title={`${userName} — balans`} onClose={onClose}>
      <div className={styles.body}>
        <div className={styles.balanceRow}>
          <span>Joriy balans</span>
          <strong className={balance < 0 ? styles.debt : styles.ok}>{formatMoney(balance)} UZS</strong>
        </div>

        {balance < 0 && (
          <div className={styles.warning}>
            Balans manfiy — haydovchi bo'lsa u avtomatik bloklangan. To'ldirilib 0 dan yuqori
            bo'lganda blok o'zi yechiladi.
          </div>
        )}

        <div className={styles.signRow}>
          <button
            className={sign === 'plus' ? styles.signActive : styles.sign}
            onClick={() => setSign('plus')}
          >
            + To'ldirish
          </button>
          <button
            className={sign === 'minus' ? styles.signActiveMinus : styles.sign}
            onClick={() => setSign('minus')}
          >
            − Yechish
          </button>
        </div>

        <div className={styles.formRow}>
          <input
            className={styles.input}
            inputMode="numeric"
            placeholder="Summa (UZS)"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <input
            className={styles.input}
            placeholder="Izoh (ixtiyoriy)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button className={shared.primaryBtn} disabled={saving || !amount.trim()} onClick={submit}>
            {saving ? '...' : 'Qo‘llash'}
          </button>
        </div>

        {error && <div className={shared.errorBanner}>{error}</div>}

        <div className={styles.historyHead}>Oxirgi harakatlar</div>
        {loading ? (
          <div className={styles.muted}>Yuklanmoqda...</div>
        ) : items.length === 0 ? (
          <div className={styles.muted}>Hozircha balans harakati yo‘q</div>
        ) : (
          <ul className={styles.history}>
            {items.map((tx) => (
              <li key={tx.id} className={styles.historyItem}>
                <div>
                  <div className={styles.txType}>
                    {TYPE_LABEL[tx.type] ?? tx.type}
                    {tx.order_id != null && <span className={styles.txOrder}> · buyurtma #{tx.order_id}</span>}
                  </div>
                  {tx.note && <div className={styles.txNote}>{tx.note}</div>}
                  <div className={styles.txDate}>{formatDateTime(tx.created_at)}</div>
                </div>
                <div className={styles.txAmountBox}>
                  <div className={tx.amount < 0 ? styles.debt : styles.ok}>
                    {tx.amount > 0 ? '+' : ''}
                    {formatMoney(tx.amount)}
                  </div>
                  <div className={styles.txAfter}>→ {formatMoney(tx.balance_after)}</div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}
