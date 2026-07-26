import { useEffect, useState } from 'react';
import { ApiError } from '../api/client';
import { listMyBalanceTransactions } from '../api/drivers';
import type { BalanceTransaction } from '../types/api';
import { formatPrice } from '../utils/format';
import styles from './BalanceCard.module.css';

interface Props {
  balance: number;
  currency: string;
}

const HISTORY_LIMIT = 20;

const TYPE_LABEL: Record<string, string> = {
  ORDER_COMMISSION: 'Tizim komissiyasi',
  ADMIN_ADJUSTMENT: "To'ldirish / tuzatish",
};

/** "26.07.2026 15:06" — `toLocaleDateString('uz-UZ')` oy nomini "M07" deb berardi. */
function formatDate(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)}.${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Profil sahifasidagi balans bloki: joriy balans + harakatlar tarixi.
 *  (Ilgari bosh sahifadagi qora kartochkada faqat summa ko'rinardi.) */
export function BalanceCard({ balance, currency }: Props) {
  const [items, setItems] = useState<BalanceTransaction[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listMyBalanceTransactions({ limit: HISTORY_LIMIT })
      .then((rows) => !cancelled && setItems(rows))
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : 'Tarix yuklanmadi');
        setItems([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const visible = expanded ? items ?? [] : (items ?? []).slice(0, 5);
  const hasMore = (items?.length ?? 0) > 5;

  return (
    <div className={styles.card}>
      <div className={styles.head}>
        <span className={styles.label}>Joriy balans</span>
        <span className={balance < 0 ? styles.valueDebt : styles.value}>
          {formatPrice(balance)} <span className={styles.currency}>{currency}</span>
        </span>
      </div>

      {balance < 0 && (
        <div className={styles.debtNote}>
          Balans manfiy — qarz yopilmaguncha liniyaga chiqa olmaysiz. To'lov uchun
          administratsiyaga murojaat qiling.
        </div>
      )}

      <div className={styles.historyHead}>Harakatlar tarixi</div>

      {items === null && <div className={styles.muted}>Yuklanmoqda...</div>}
      {error && <div className={styles.muted}>{error}</div>}
      {items !== null && items.length === 0 && !error && (
        <div className={styles.muted}>Hozircha balans harakati yo‘q</div>
      )}

      {visible.length > 0 && (
        <ul className={styles.list}>
          {visible.map((tx) => {
            const amount = Number(tx.amount);
            return (
              <li key={tx.id} className={styles.item}>
                <div className={styles.itemLeft}>
                  <div className={styles.itemTitle}>
                    {TYPE_LABEL[tx.type] ?? tx.type}
                    {tx.order_id != null && <span className={styles.itemOrder}> · #{tx.order_id}</span>}
                  </div>
                  <div className={styles.itemDate}>{formatDate(tx.created_at)}</div>
                </div>
                <div className={styles.itemRight}>
                  <div className={amount < 0 ? styles.amountOut : styles.amountIn}>
                    {amount > 0 ? '+' : '−'}
                    {formatPrice(Math.abs(amount))}
                  </div>
                  <div className={styles.itemAfter}>{formatPrice(Number(tx.balance_after))}</div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {hasMore && (
        <button className={styles.moreBtn} onClick={() => setExpanded((v) => !v)}>
          {expanded ? 'Yopish' : `Yana ${(items?.length ?? 0) - 5} ta ko‘rsatish`}
        </button>
      )}
    </div>
  );
}
