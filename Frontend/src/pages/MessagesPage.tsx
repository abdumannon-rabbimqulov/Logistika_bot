import { BottomNav } from '../components/BottomNav';
import { MessagesNavIcon } from '../components/icons';
import styles from './MessagesPage.module.css';

// Backendda xabar almashish tizimi hali yo'q — shuning uchun bu yerda funksional
// emas, faqat "tez orada" ekrani.
export function MessagesPage() {
  return (
    <div className={styles.page}>
      <div className={styles.topBar}>
        <div className={styles.title}>Xabarlar</div>
      </div>
      <div className={styles.empty}>
        <MessagesNavIcon size={40} color="var(--color-gray-300)" strokeWidth={1.5} />
        <div className={styles.emptyTitle}>Tez orada</div>
        <div className={styles.emptyHint}>Xabarlar bo'limi hali ishlab chiqilmoqda</div>
      </div>
      <BottomNav />
    </div>
  );
}
