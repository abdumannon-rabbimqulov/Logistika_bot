import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError } from '../api/client';
import { bumpPrice, cancelOrder, getOrder, getPriceOptions } from '../api/orders';
import { BottomSheet } from '../components/BottomSheet';
import { BackIcon, PhoneIcon, SendIcon, StarIcon } from '../components/icons';
import { YandexMap } from '../components/YandexMap';
import { useOrderDriverLocation } from '../hooks/useOrderDriverLocation';
import type { OrderDetail, QuickPriceOption, WaypointStatus, WaypointType } from '../types/api';
import { formatPrice, routeLabel, statusLabel } from '../utils/format';
import { describePickupAt } from '../utils/pickupTime';
import styles from './OrderTrackingPage.module.css';

const MAX_ROUNDS = 5; // services/dispatch.py MAX_ROUNDS bilan mos
const POLL_INTERVAL_MS = 5000;
// Qidiruv boshlanishini kutayotgan buyurtma uchun (holat soatlab o'zgarmaydi)
const SCHEDULED_POLL_INTERVAL_MS = 60_000;

const WAYPOINT_TYPE_LABEL: Record<WaypointType, string> = {
  PICKUP: 'Yuk ortish',
  DELIVERY: 'Yetkazish',
  TRANSIT: 'Oraliq nuqta',
};

const WAYPOINT_STATUS_LABEL: Record<WaypointStatus, string> = {
  PENDING: 'Kutilmoqda',
  ARRIVED: 'Yetib keldi',
  COMPLETED: 'Yakunlandi',
  SKIPPED: 'O‘tkazib yuborildi',
};

/** ISO vaqtdan faqat soat:daqiqa (bosqichlar ro'yxati uchun). */
function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' });
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function OrderTrackingPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [bumping, setBumping] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  // Bekor qilish qaytarib bo'lmaydigan amal — tugma bosilganda o'sha joyning o'zida
  // tasdiq so'raladi (Telegram WebApp'da `window.confirm` ishonchli emas).
  const [confirmingCancel, setConfirmingCancel] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Narx oshirish tugmalari — qiymatlarni backend beradi (bot bilan bir xil ro'yxat)
  const [priceOptions, setPriceOptions] = useState<QuickPriceOption[]>([]);
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
    // Qidiruv hali boshlanmagan bo'lsa (kelajakdagi yuk) tez-tez so'rash bekor —
    // holat soatlab o'zgarmaydi. Boshlangach odatdagi tezlikka qaytadi.
    const interval = order.dispatch_starts_at ? SCHEDULED_POLL_INTERVAL_MS : POLL_INTERVAL_MS;
    timerRef.current = setTimeout(load, interval);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [order, load]);

  // Taklif tushgach variantlarni backend'dan olamiz. Narxni frontend HISOBLAMAYDI:
  // aks holda web va bot turli summalarni ko'rsatardi va chegara tekshiruvi
  // (services/pricing.py) ikki joyda takrorlanardi.
  const bumpOffered = Boolean(order?.price_bump_requested_at) && order?.driver_id == null;
  // Effekt butun `order` obyektiga bog'lanmasin: u har so'rovda yangi havola bo'ladi
  // va variantlar keraksiz qayta yuklanardi. Faqat shu ikki maydon muhim.
  const orderIdForOptions = order?.id ?? null;
  const orderPrice = order?.price ?? null;
  useEffect(() => {
    if (orderIdForOptions == null || !bumpOffered) {
      setPriceOptions([]);
      return;
    }
    let cancelled = false;
    void getPriceOptions(orderIdForOptions)
      .then((data) => {
        if (!cancelled) setPriceOptions(data.quick_price_options);
      })
      .catch(() => {
        if (!cancelled) setPriceOptions([]);
      });
    return () => {
      cancelled = true;
    };
    // `orderPrice` — bump'dan keyin variantlar yangi narxdan qayta hisoblanishi uchun
  }, [orderIdForOptions, orderPrice, bumpOffered]);

  async function handleBump(newPrice: number) {
    if (!order) return;
    setBumping(true);
    setError(null);
    try {
      const updated = await bumpPrice(order.id, newPrice);
      setOrder(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Narxni oshirib bo'lmadi");
    } finally {
      setBumping(false);
    }
  }

  async function handleCancel() {
    if (!order) return;
    setCancelling(true);
    setError(null);
    try {
      await cancelOrder(order.id);
      setConfirmingCancel(false);
      // Javob 204 (tanasi yo'q) — yangilangan holatni qayta o'qiymiz. Status
      // `CANCELLED` bo'lgach so'rovlar (polling) `useEffect` ichida o'zi to'xtaydi.
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Buyurtmani bekor qilib bo'lmadi");
    } finally {
      setCancelling(false);
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
  const awaitingBump = bumpOffered;
  // Backend hisoblab beradi (`order/schemas.py dispatch_starts_at`) — lead vaqti
  // sozlamasi frontendda takrorlanmasin.
  const scheduledStart = order.dispatch_starts_at ? new Date(order.dispatch_starts_at) : null;
  // Haydovchi biriktirilmagan bo'lsa mijoz buyurtmadan voz kecha oladi. Backend ham
  // shu shartni qo'llaydi (`DELETE /orders/{id}` IN_PROGRESS da 422 qaytaradi).
  const canCancel = order.status === 'PENDING' && order.driver_id == null;
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
  // Kamida bitta koordinata bo'lsa xarita chizishga arziydi (haydovchi hali
  // biriktirilmagan bo'lsa ham marshrut ko'rinib turadi).
  const hasRoutePoints = originPoint != null || destinationPoint != null;

  return (
    <div className={styles.page}>
      {/* Xarita — sahifaning foni. Marshrut koordinatalari bo'lsa doim ko'rsatiladi
          (ilgari faqat haydovchi biriktirilganda chizilardi), haydovchi nuqtasi esa
          kuzatuv mumkin bo'lganda qo'shiladi. */}
      <div className={styles.mapLayer}>
        {hasRoutePoints ? (
          <YandexMap
            origin={originPoint}
            destination={destinationPoint}
            driverLocation={driverLocation}
          />
        ) : (
          <div className={styles.mapPlaceholder}>Marshrut xaritasi mavjud emas</div>
        )}
      </div>

      <div className={styles.topBar}>
        <button className={styles.backBtn} onClick={() => navigate('/')}>
          <BackIcon />
        </button>
        <span className={styles.title}>Buyurtma #{order.id}</span>
      </div>

      <BottomSheet
        initialSnap={isTrackable ? 'peek' : 'half'}
        header={
          <>
            <span className={styles.sheetTitle}>{statusLabel(order.status)}</span>
            <span className={styles.sheetPrice}>
              {formatPrice(order.price)} {order.currency}
            </span>
          </>
        }
      >
      <div className={styles.section}>
        <div className={styles.statusCard}>
          <span className={styles.statusLabel}>{statusLabel(order.status)}</span>
          <div className={styles.statusHeadline}>
            {isSearching && !awaitingBump && !scheduledStart && 'Haydovchi qidirilmoqda...'}
            {scheduledStart && 'Buyurtma rejalashtirildi'}
            {isFound && 'Haydovchi topildi!'}
            {order.status === 'COMPLETED' && "Buyurtma yakunlandi"}
            {order.status === 'CANCELLED' && 'Buyurtma bekor qilindi'}
            {awaitingBump && "Hozircha haydovchi topilmadi"}
          </div>

          {/* Kelajakka rejalashtirilgan yuk: qidiruv hali boshlanmagan. Progress
              ko'rsatkichi bu yerda chalg'ituvchi bo'lardi ("0/5 haydovchi javob
              kutilmoqda" — aslida hech kimga yuborilmagan). */}
          {scheduledStart && (
            <div className={styles.scheduledNote}>
              Yuk {describePickupAt(new Date(order.pickup_at))} ga rejalashtirilgan.
              <br />
              Haydovchi qidiruvi {describePickupAt(scheduledStart)} da boshlanadi.
            </div>
          )}

          {isSearching && !awaitingBump && !scheduledStart && (
            <>
              <div className={styles.progressTrack}>
                <div className={styles.progressFill} style={{ width: `${progressPercent}%` }} />
              </div>
              <div className={styles.progressHint}>
                {order.dispatch_round}/{MAX_ROUNDS} haydovchidan javob kutilmoqda
              </div>
            </>
          )}

          {/* Voz kechish yo'li butun qidiruv davomida ochiq: mijoz "haydovchi topilmadi"
              xabarini kutib o'tirmasdan ham buyurtmadan qaytishi mumkin. Haydovchi
              biriktirilgach tugma yo'qoladi (kelishilgan ishni bir tomonlama bekor
              qilish — alohida masala, backend uni IN_PROGRESS da taqiqlaydi). */}
          {canCancel && !confirmingCancel && (
            <button
              className={styles.cancelBtn}
              disabled={cancelling}
              onClick={() => setConfirmingCancel(true)}
            >
              Buyurtmani bekor qilish
            </button>
          )}
          {canCancel && confirmingCancel && (
            <div className={styles.cancelConfirm}>
              <div className={styles.cancelConfirmText}>Buyurtma bekor qilinsinmi?</div>
              <div className={styles.cancelConfirmActions}>
                <button
                  className={styles.cancelConfirmBtn}
                  disabled={cancelling}
                  onClick={handleCancel}
                >
                  {cancelling ? 'Bekor qilinmoqda...' : 'Ha, bekor qilinsin'}
                </button>
                <button
                  className={styles.cancelBackBtn}
                  disabled={cancelling}
                  onClick={() => setConfirmingCancel(false)}
                >
                  Yo'q
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {isTrackable && !driverLocation && (
        <div className={styles.section}>
          <div className={styles.mapHint}>Haydovchining jonli joylashuvi kutilmoqda...</div>
        </div>
      )}

      {/* ── Haydovchi va aloqa ────────────────────────────────────────────────
          Telefon `tel:` bilan qo'ng'iroqni, `telegram_url` esa suhbatni ochadi
          (backend `https://t.me/{username}` shaklida tayyorlab beradi —
          `order/schemas.py OrderDetailResponse.from_order`). */}
      {order.driver_contact && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>Haydovchi</div>
          <div className={styles.driverCard}>
            <div className={styles.contactInfo}>
              <div className={styles.contactName}>{order.driver_contact.full_name}</div>
              <div className={styles.contactMeta}>
                <StarIcon size={13} />
                {Number(order.driver_contact.rating).toFixed(1)}
                {order.driver_contact.truck_type_name && ` · ${order.driver_contact.truck_type_name}`}
                {` · ${order.driver_contact.truck_number}`}
              </div>
            </div>

            <div className={styles.contactLinks}>
              {order.driver_contact.phone_number && (
                <a className={styles.contactLink} href={`tel:${order.driver_contact.phone_number}`}>
                  <PhoneIcon />
                  <span className={styles.contactLinkText}>
                    {order.driver_contact.phone_number}
                  </span>
                </a>
              )}
              {order.driver_contact.telegram_url && (
                <a
                  className={styles.contactLink}
                  href={order.driver_contact.telegram_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  <SendIcon />
                  <span className={styles.contactLinkText}>
                    @{order.driver_contact.username}
                  </span>
                </a>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Yo'l statuslari ──────────────────────────────────────────────────
          Har bir nuqta va uning holati. Haydovchi qadamlarni belgilagan sari
          (`PATCH /orders/{id}/waypoints/{wp}`) bu ro'yxat yangilanadi. */}
      {order.waypoints.length > 0 && (
        <div className={styles.section}>
          <div className={styles.sectionTitle}>Yo'l bosqichlari</div>
          <ol className={styles.timeline}>
            {order.waypoints.map((wp) => {
              const done = wp.status === 'COMPLETED';
              const skipped = wp.status === 'SKIPPED';
              const active = wp.id === order.current_waypoint?.id;
              return (
                <li
                  key={wp.id}
                  className={`${styles.timelineItem} ${active ? styles.timelineActive : ''}`}
                >
                  <span
                    className={`${styles.timelineDot} ${
                      done ? styles.timelineDotDone : skipped ? styles.timelineDotSkipped : ''
                    }`}
                  />
                  <div className={styles.timelineBody}>
                    <div className={styles.timelineHead}>
                      <span className={styles.timelineType}>{WAYPOINT_TYPE_LABEL[wp.type]}</span>
                      <span className={styles.timelineStatus}>
                        {WAYPOINT_STATUS_LABEL[wp.status]}
                      </span>
                    </div>
                    <div className={styles.timelineAddress}>{wp.address ?? 'Manzil ko‘rsatilmagan'}</div>
                    {(wp.arrived_at || wp.completed_at) && (
                      <div className={styles.timelineTime}>
                        {wp.arrived_at && `Yetib keldi: ${formatTime(wp.arrived_at)}`}
                        {wp.arrived_at && wp.completed_at && ' · '}
                        {wp.completed_at && `Yakunlandi: ${formatTime(wp.completed_at)}`}
                      </div>
                    )}
                    {wp.contact_name && (
                      <div className={styles.timelineContact}>
                        {wp.contact_name}
                        {wp.contact_phone && (
                          <a className={styles.timelinePhone} href={`tel:${wp.contact_phone}`}>
                            {wp.contact_phone}
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {awaitingBump && (
        <div className={styles.section}>
          <div className={styles.bumpBox}>
            <div className={styles.bumpText}>
              {order.dispatch_round > 0
                ? `${order.dispatch_round} ta haydovchidan hech biri javob bermadi.`
                : 'Hozircha mos haydovchi topilmadi.'}{' '}
              Narxni oshirib qidiruvni davom ettiramizmi?
            </div>
            <div className={styles.bumpButtons}>
              {priceOptions.map((option) => (
                <button
                  key={option.increment}
                  className={styles.bumpBtn}
                  disabled={bumping}
                  onClick={() => handleBump(option.price)}
                >
                  +{formatPrice(option.increment)} ({formatPrice(option.price)})
                </button>
              ))}
            </div>
            {error && <div className={styles.errorText}>{error}</div>}
          </div>
        </div>
      )}

      <div className={styles.section}>
        <div className={styles.sectionTitle}>Buyurtma ma'lumotlari</div>
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

          <dl className={styles.detailList}>
            <div className={styles.detailRow}>
              <dt>Yuk</dt>
              <dd>{order.cargo_name}</dd>
            </div>
            <div className={styles.detailRow}>
              <dt>Og'irligi</dt>
              <dd>
                {order.weight} t{order.volume ? ` · ${order.volume} m³` : ''}
              </dd>
            </div>
            {order.total_distance_km != null && (
              <div className={styles.detailRow}>
                <dt>Masofa</dt>
                <dd>{Math.round(order.total_distance_km)} km</dd>
              </div>
            )}
            <div className={styles.detailRow}>
              <dt>Yuklash vaqti</dt>
              <dd>{formatDateTime(order.pickup_at)}</dd>
            </div>
            {order.original_price != null && order.original_price !== order.price && (
              <div className={styles.detailRow}>
                <dt>Dastlabki narx</dt>
                <dd className={styles.detailMuted}>
                  {formatPrice(order.original_price)} {order.currency}
                </dd>
              </div>
            )}
            <div className={styles.detailRow}>
              <dt>Narx</dt>
              <dd className={styles.priceValue}>
                {formatPrice(order.price)} {order.currency}
              </dd>
            </div>
          </dl>

          {order.overload_warning && <div className={styles.errorText}>{order.overload_warning}</div>}
        </div>
      </div>
      </BottomSheet>
    </div>
  );
}
