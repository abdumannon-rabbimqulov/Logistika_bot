import { NavLink, Outlet } from 'react-router-dom';
import { clearTokens } from '../api/client';
import {
  DashboardIcon,
  DriversIcon,
  LogoutIcon,
  OrdersIcon,
  SettingsIcon,
  TruckTypesIcon,
  UsersIcon,
} from './icons';
import styles from './AdminLayout.module.css';

const NAV = [
  { to: '/admin', label: 'Dashboard', Icon: DashboardIcon, end: true },
  { to: '/admin/orders', label: 'Buyurtmalar', Icon: OrdersIcon, end: false },
  { to: '/admin/drivers', label: 'Haydovchilar', Icon: DriversIcon, end: false },
  { to: '/admin/users', label: 'Foydalanuvchilar', Icon: UsersIcon, end: false },
  { to: '/admin/truck-types', label: 'Transport turlari', Icon: TruckTypesIcon, end: false },
  { to: '/admin/settings', label: 'Sozlamalar', Icon: SettingsIcon, end: false },
];

function handleLogout() {
  clearTokens();
  window.location.reload();
}

export function AdminLayout() {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>YUK</span>
          <span className={styles.brandSub}>Admin</span>
        </div>

        <nav className={styles.nav}>
          {NAV.map(({ to, label, Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => (isActive ? styles.navItemActive : styles.navItem)}
            >
              <Icon />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <button className={styles.logout} onClick={handleLogout}>
          <LogoutIcon />
          <span>Chiqish</span>
        </button>
      </aside>

      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  );
}
