import { NavLink } from 'react-router-dom';
import styles from './BottomNav.module.css';
import { HomeNavIcon, MessagesNavIcon, OrdersNavIcon, ProfileIcon } from './icons';

const ITEMS = [
  { to: '/', label: 'Bosh sahifa', Icon: HomeNavIcon, exact: true },
  { to: '/orders', label: 'Buyurtmalar', Icon: OrdersNavIcon, exact: false },
  { to: '/messages', label: 'Xabarlar', Icon: MessagesNavIcon, exact: false },
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
