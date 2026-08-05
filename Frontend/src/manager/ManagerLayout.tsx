import { NavLink, Outlet } from 'react-router-dom';
import { clearTokens } from '../api/client';
import { LogoutIcon, OrdersIcon, TicketsIcon } from '../admin/icons';
// Qobiq uslublari admin panel bilan aynan bir xil — nusxa ko'chirmasdan qayta ishlatamiz.
import styles from '../admin/AdminLayout.module.css';

const NAV = [
  { to: '/manager/orders', label: 'Buyurtmalar', Icon: OrdersIcon, end: false },
  { to: '/manager/tickets', label: 'Murojaatlar', Icon: TicketsIcon, end: false },
];

function handleLogout() {
  clearTokens();
  window.location.reload();
}

export function ManagerLayout() {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          <span className={styles.brandMark}>YUK</span>
          <span className={styles.brandSub}>Menejer</span>
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
