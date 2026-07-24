import type { ReactNode } from 'react';
import styles from './DataTable.module.css';

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  align?: 'left' | 'right' | 'center';
  width?: string;
}

interface Props<T> {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  loading?: boolean;
  error?: string | null;
  emptyText?: string;
  onRowClick?: (row: T) => void;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  loading = false,
  error = null,
  emptyText = "Ma'lumot yo'q",
  onRowClick,
}: Props<T>) {
  return (
    <div className={styles.wrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} style={{ textAlign: col.align ?? 'left', width: col.width }}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading &&
            Array.from({ length: 6 }).map((_, i) => (
              <tr key={`sk-${i}`} className={styles.skeletonRow}>
                {columns.map((col) => (
                  <td key={col.key}>
                    <span className={styles.skeleton} />
                  </td>
                ))}
              </tr>
            ))}

          {!loading &&
            rows.map((row) => (
              <tr
                key={rowKey(row)}
                className={onRowClick ? styles.clickable : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((col) => (
                  <td key={col.key} style={{ textAlign: col.align ?? 'left' }}>
                    {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
        </tbody>
      </table>

      {!loading && error && <div className={styles.error}>{error}</div>}
      {!loading && !error && rows.length === 0 && <div className={styles.empty}>{emptyText}</div>}
    </div>
  );
}
