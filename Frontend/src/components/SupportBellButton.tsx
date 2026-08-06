import { useNavigate } from 'react-router-dom';
import { BellIcon } from './icons';
import styles from './SupportBellButton.module.css';

// Murojaatlar (support) bo'limiga yagona kirish nuqtasi — ekranning yuqori o'ng
// burchagidagi qo'ng'iroq tugmasi. Pastki menyuda "Xabarlar" bandi yo'q
// (`BottomNav.tsx`), shuning uchun sender ko'radigan har bir asosiy ekranda shu
// tugma turishi kerak — aks holda bo'lim faqat bosh sahifadan ochilardi.

export function SupportBellButton() {
  const navigate = useNavigate();

  return (
    <button
      className={styles.iconCircle}
      onClick={() => navigate('/messages')}
      aria-label="Murojaatlar"
    >
      <BellIcon />
    </button>
  );
}
