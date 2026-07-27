import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { bumpPrice, getOrder } from '../api/orders';
import { BackIcon, PhoneIcon, SendIcon, StarIcon } from '../components/icons';
import { YandexMap } from '../components/YandexMap';
import { useOrderDriverLocation } from '../hooks/useOrderDriverLocation';
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

  // Haydovchi biriktirilgan va yo'lda bo'lsa — jonli joylashuvi kuzatiladi
  // (order/router.py `WS /orders/{id}/ws/driver-location`). Hook har renderda
  // bir xil tartibda chaqirilishi shart, shuning uchun quyidagi `if (!order)`
  // ERTA return'idan OLDIN turadi — `order` hali `null` bo'lsa `enabled=false`.
  const isFound =
    order != null &&
    (order.status === 'SCHEDULED' || order.status === 'ACCEPTED' || order.status === 'IN_PROGRESS');
  const isTrackable = isFound && order?.driver_id != null;
  const driverPoint = useOrderDriverLocation(order?.id ?? null, isTrackable);

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
  const awaitingBump = Boolean(order.price_bump_requested_at) && order.driver_id === null;
  const progressPercent = Math.min(100, (order.dispatch_round / MAX_ROUNDS) * 100);
  const driverLocation = driverPoint
    ? { latitude: driverPoint.latitude, longitude: driverPoint.longitude }
    : null;
  const originPoint =
    order.origin?.latitude != null && order.origin.longitude != null
      ? { latitude: order.origin.latitude, longitude: order.origin.longitude }
      : null;
  const destinationPoint =
    order.destination?.latitude != null && order.destination.longitude != null
      ? { latitude: order.destination.latitude, longitude: order.destination.longitude }
      : null;

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

      {isTrackable && (
        <div className={styles.section}>
          <div className={styles.mapCard}>
            <YandexMap
              origin={originPoint}
              destination={destinationPoint}
              driverLocation={driverLocation}
            />
          </div>
          {!driverLocation && (
            <div className={styles.mapHint}>Haydovchining jonli joylashuvi kutilmoqda...</div>
          )}
        </div>
      )}

      {order.driver_contact && (
        <div className={styles.section}>
          <div className={styles.contactCard}>
            <div className={styles.contactInfo}>
              <div className={styles.contactName}>{order.driver_contact.full_name}</div>
              <div className={styles.contactMeta}>
                <StarIcon size={13} />
                {Number(order.driver_contact.rating).toFixed(1)}
                {order.driver_contact.truck_type_name && ` · ${order.driver_contact.truck_type_name}`}
                {` · ${order.driver_contact.truck_number}`}
              </div>
            </div>
            <div className={styles.contactActions}>
              {order.driver_contact.phone_number && (
                <a
                  className={styles.contactBtn}
                  href={`tel:${order.driver_contact.phone_number}`}
                  aria-label="Haydovchiga qo'ng'iroq qilish"
                >
                  <PhoneIcon />
                </a>
              )}
              {order.driver_contact.telegram_url && (
                <a
                  className={styles.contactBtn}
                  href={order.driver_contact.telegram_url}
                  target="_blank"
                  rel="noreferrer"
                  aria-label="Haydovchiga Telegram orqali yozish"
                >
                  <SendIcon />
                </a>
              )}
            </div>
          </div>
        </div>
      )}

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
