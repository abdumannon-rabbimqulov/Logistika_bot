import { NavLink } from 'react-router-dom';
import styles from './BottomNav.module.css';
import { HomeNavIcon, OrdersNavIcon, ProfileIcon } from './icons';

// Murojaatlar (`/messages`) ATAYLAB bu yerda yo'q: unga kirish yuqori o'ng
// burchakdagi qo'ng'iroq tugmasi orqali beriladi (`TopBarActions`). Shu bilan
// haydovchi menyusi bilan ham bir xil bo'ladi — u yerda ham pastda "Xabarlar"
// yo'q (`DriverBottomNav.tsx`), murojaatlar profil ichidan ochiladi.
const ITEMS = [
  { to: '/', label: 'Bosh sahifa', Icon: HomeNavIcon, exact: true },
  { to: '/orders', label: 'Buyurtmalar', Icon: OrdersNavIcon, exact: false },
  { to: '/profile', label: 'Profil', Icon: ProfileIcon, exact: false },
];

export function BottomNav() {
  return (
    <nav className={styles.nav}>
      {ITEMS.map(({ to, label, Icon }) => (
        <NavLink key={to} to={to} end={to === '/'} className={styles.item}>
          {({ isActive }) => (
            <>
              <Icon color={isActive ? 'var(--color-accent)' : 'var(--color-gray-500)'} />
              <span className={isActive ? styles.labelActive : styles.label}>{label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
