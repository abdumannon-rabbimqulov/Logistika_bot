import { NavLink } from 'react-router-dom';
import styles from './BottomNav.module.css';
import { EarningsNavIcon, HomeNavIcon, OrdersNavIcon, ProfileIcon } from './icons';

const ITEMS = [
  { to: '/', label: 'Bosh sahifa', Icon: HomeNavIcon },
  { to: '/orders', label: 'Buyurtmalar', Icon: OrdersNavIcon },
  { to: '/earnings', label: 'Daromad', Icon: EarningsNavIcon },
  { to: '/profile', label: 'Profil', Icon: ProfileIcon },
];

export function DriverBottomNav() {
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
