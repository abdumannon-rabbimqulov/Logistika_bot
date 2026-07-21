import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { listMyOrders } from '../api/orders';
import { BottomNav } from '../components/BottomNav';
import type { OrderListItem } from '../types/api';
import { formatPrice, formatRelativeDate, statusLabel } from '../utils/format';
import styles from './OrdersListPage.module.css';

export function OrdersListPage() {
  const navigate = useNavigate();
  const [orders, setOrders] = useState<OrderListItem[] | null>(null);

  useEffect(() => {
    listMyOrders()
      .then(setOrders)
      .catch(() => setOrders([]));
  }, []);

  return (
    <div className={styles.page}>
      <div className={styles.topBar}>
        <div className={styles.title}>Buyurtmalar</div>
      </div>

      {orders === null && <div className={styles.empty}>Yuklanmoqda...</div>}
      {orders?.length === 0 && <div className={styles.empty}>Hali buyurtmalar yo'q</div>}

      <div className={styles.list}>
        {orders?.map((order) => (
          <button key={order.id} className={styles.card} onClick={() => navigate(`/orders/${order.id}`)}>
            <div>
              <div className={styles.cargoName}>{order.cargo_name}</div>
              <div className={styles.meta}>
                {formatRelativeDate(order.created_at)} · {statusLabel(order.status)}
              </div>
            </div>
            <span className={styles.price}>{formatPrice(order.price)} {order.currency}</span>
          </button>
        ))}
      </div>

      <BottomNav />
    </div>
  );
}
