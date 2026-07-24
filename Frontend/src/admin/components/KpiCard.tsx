import type { ReactNode } from 'react';
import styles from './KpiCard.module.css';

interface Props {
  label: string;
  value: ReactNode;
  sub?: string;
  accent?: boolean;
  loading?: boolean;
}

export function KpiCard({ label, value, sub, accent = false, loading = false }: Props) {
  return (
    <div className={accent ? styles.cardAccent : styles.card}>
      <div className={styles.label}>{label}</div>
      {loading ? (
        <div className={styles.skeleton} />
      ) : (
        <div className={styles.value}>{value}</div>
      )}
      {sub && !loading && <div className={styles.sub}>{sub}</div>}
    </div>
  );
}
