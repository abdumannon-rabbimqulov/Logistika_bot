import styles from './Pagination.module.css';

interface Props {
  skip: number;
  limit: number;
  /** Joriy sahifadagi qatorlar soni — keyingi sahifa bor-yo'qligini bilish uchun. */
  count: number;
  total?: number;
  onChange: (skip: number) => void;
}

export function Pagination({ skip, limit, count, total, onChange }: Props) {
  const page = Math.floor(skip / limit) + 1;
  const hasPrev = skip > 0;
  const hasNext = total != null ? skip + limit < total : count >= limit;

  const from = count === 0 ? 0 : skip + 1;
  const to = skip + count;

  return (
    <div className={styles.bar}>
      <span className={styles.info}>
        {from}–{to}
        {total != null ? ` / ${total}` : ''}
      </span>
      <div className={styles.controls}>
        <button className={styles.btn} disabled={!hasPrev} onClick={() => onChange(Math.max(0, skip - limit))}>
          ← Oldingi
        </button>
        <span className={styles.page}>{page}</span>
        <button className={styles.btn} disabled={!hasNext} onClick={() => onChange(skip + limit)}>
          Keyingi →
        </button>
      </div>
    </div>
  );
}
