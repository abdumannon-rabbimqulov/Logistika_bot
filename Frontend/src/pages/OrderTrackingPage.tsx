import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { bumpPrice, getOrder } from '../api/orders';
import { BackIcon } from '../components/icons';
import type { OrderDetail } from '../types/api';
import { formatPrice, routeLabel, statusLabel } from '../utils/format';
import styles from './OrderTrackingPage.module.css';

const MAX_ROUNDS = 5; // services/dispatch.py MAX_ROUNDS bilan mos
const POLL_INTERVAL_MS = 5000;

export function OrderTrackingPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [bumping, setBumping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    if (!orderId) return;
    try {
      const data = await getOrder(Number(orderId));
      setOrder(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Buyurtma topilmadi");
    }
  }, [orderId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!order || order.status !== 'PENDING') {
      if (timerRef.current) clearTimeout(timerRef.current);
      return;
    }
    timerRef.current = setTimeout(load, POLL_INTERVAL_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [order, load]);

  async function handleBump(percent: number) {
    if (!order) return;
    setBumping(true);
    setError(null);
    try {
      const newPrice = Math.round(order.price * (1 + percent / 100));
      const updated = await bumpPrice(order.id, newPrice);
      setOrder(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Narxni oshirib bo'lmadi");
    } finally {
      setBumping(false);
    }
  }

  if (!order) {
    return (
      <div className={styles.page}>
        <div className={styles.topBar}>
          <button className={styles.backBtn} onClick={() => navigate('/')}>
            <BackIcon />
          </button>
          <span className={styles.title}>Buyurtma</span>
        </div>
        {error && (
          <div className={styles.section}>
            <div className={styles.errorText}>{error}</div>
          </div>
        )}
      </div>
    );
  }

  const isSearching = order.status === 'PENDING';
  const isFound = order.status === 'ACCEPTED' || order.status === 'IN_PROGRESS';
  const awaitingBump = Boolean(order.price_bump_requested_at) && order.driver_id === null;
  const progressPercent = Math.min(100, (order.dispatch_round / MAX_ROUNDS) * 100);

  return (
    <div className={styles.page}>
      <div className={styles.topBar}>
        <button className={styles.backBtn} onClick={() => navigate('/')}>
          <BackIcon />
        </button>
        <span className={styles.title}>Buyurtma #{order.id}</span>
      </div>

      <div className={styles.section}>
        <div className={styles.statusCard}>
          <span className={styles.statusLabel}>{statusLabel(order.status)}</span>
          <div className={styles.statusHeadline}>
            {isSearching && !awaitingBump && 'Haydovchi qidirilmoqda...'}
            {isFound && 'Haydovchi topildi!'}
            {order.status === 'COMPLETED' && "Buyurtma yakunlandi"}
            {order.status === 'CANCELLED' && 'Buyurtma bekor qilindi'}
            {awaitingBump && "Hozircha haydovchi topilmadi"}
          </div>
          {isSearching && !awaitingBump && (
            <>
              <div className={styles.progressTrack}>
                <div className={styles.progressFill} style={{ width: `${progressPercent}%` }} />
              </div>
              <div className={styles.progressHint}>
                {order.dispatch_round}/{MAX_ROUNDS} haydovchidan javob kutilmoqda
              </div>
            </>
          )}
        </div>
      </div>

      {awaitingBump && (
        <div className={styles.section}>
          <div className={styles.bumpBox}>
            <div className={styles.bumpText}>
              {MAX_ROUNDS} ta haydovchidan hech biri javob bermadi. Narxni oshirib qidiruvni davom ettiramizmi?
            </div>
            <div className={styles.bumpButtons}>
              <button className={styles.bumpBtn} disabled={bumping} onClick={() => handleBump(10)}>
                +10% ({formatPrice(order.price * 1.1)})
              </button>
              <button className={styles.bumpBtn} disabled={bumping} onClick={() => handleBump(20)}>
                +20% ({formatPrice(order.price * 1.2)})
              </button>
            </div>
            {error && <div className={styles.errorText}>{error}</div>}
          </div>
        </div>
      )}

      <div className={styles.section}>
        <div className={styles.card}>
          <div className={styles.routeRow}>
            <div className={styles.routePoint}>
              <span className={styles.routeDotOrigin} />
              <span>{order.origin?.address ?? routeLabel(null, null)}</span>
            </div>
            <div className={styles.routePoint}>
              <span className={styles.routeDotDest} />
              <span>{order.destination?.address ?? '?'}</span>
            </div>
          </div>
          <div className={styles.priceRow}>
            <span className={styles.priceLabel}>
              {order.cargo_name} · {order.weight}t
              {order.total_distance_km ? ` · ${Math.round(order.total_distance_km)} km` : ''}
            </span>
            <span className={styles.priceValue}>{formatPrice(order.price)} {order.currency}</span>
          </div>
          {order.overload_warning && <div className={styles.errorText}>{order.overload_warning}</div>}
        </div>
      </div>
    </div>
  );
}
