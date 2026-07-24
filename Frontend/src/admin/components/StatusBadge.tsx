import type { OrderStatus } from '../../types/api';
import { statusLabel } from '../../utils/format';
import styles from './StatusBadge.module.css';

const TONE: Record<OrderStatus, string> = {
  SCHEDULED: styles.blue,
  PENDING: styles.amber,
  ACCEPTED: styles.green,
  IN_PROGRESS: styles.green,
  COMPLETED: styles.neutral,
  CANCELLED: styles.red,
};

export function StatusBadge({ status }: { status: OrderStatus }) {
  return <span className={`${styles.badge} ${TONE[status] ?? styles.neutral}`}>{statusLabel(status)}</span>;
}
