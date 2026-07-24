import { useEffect, useRef, useState } from 'react';
import type { DispatchAttemptResponse } from '../types/api';
import { formatPrice } from '../utils/format';
import { CheckIcon, CloseIcon, WeightIcon } from './icons';
import styles from './DispatchOfferCard.module.css';

interface Props {
  attempt: DispatchAttemptResponse;
  onAccept: () => void;
  onReject: () => void;
  onExpire: () => void;
  busy?: 'accept' | 'reject' | null;
}

const RING_RADIUS = 20;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

/** Navbat bilan kelgan taklif — 60 soniyalik countdown halqa bilan. Vaqt tugasa
 *  yoki qabul/rad etilsa tegishli callback chaqiriladi. */
export function DispatchOfferCard({ attempt, onAccept, onReject, onExpire, busy }: Props) {
  const expiresAt = new Date(attempt.expires_at).getTime();
  const sentAt = new Date(attempt.sent_at).getTime();
  // Umumiy oyna (odatda ~60s) — halqa ulushini hisoblash uchun; buzuq sana holatida 60s.
  const totalMs = expiresAt > sentAt ? expiresAt - sentAt : 60_000;

  const [remainingMs, setRemainingMs] = useState(() => Math.max(0, expiresAt - Date.now()));
  const expiredRef = useRef(false);

  useEffect(() => {
    expiredRef.current = false;
    const tick = () => {
      const left = Math.max(0, expiresAt - Date.now());
      setRemainingMs(left);
      if (left <= 0 && !expiredRef.current) {
        expiredRef.current = true;
        onExpire();
      }
    };
    tick();
    const id = window.setInterval(tick, 250);
    return () => window.clearInterval(id);
    // attempt.id o'zgarsa (yangi taklif) qaytadan ishga tushadi
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt.id]);

  const secondsLeft = Math.ceil(remainingMs / 1000);
  const fraction = Math.max(0, Math.min(1, remainingMs / totalMs));
  const dashOffset = RING_CIRCUMFERENCE * (1 - fraction);

  const order = attempt.order;
  const matchLabel = attempt.match_type === 'gps' ? 'Sizga eng yaqin' : 'Sizning hududingizda';

  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div>
          <div className={styles.kicker}>Yangi buyurtma</div>
          <div className={styles.match}>{matchLabel}</div>
        </div>
        <div className={styles.ring} role="timer" aria-label={`${secondsLeft} soniya qoldi`}>
          <svg width="52" height="52" viewBox="0 0 52 52">
            <circle cx="26" cy="26" r={RING_RADIUS} className={styles.ringTrack} />
            <circle
              cx="26"
              cy="26"
              r={RING_RADIUS}
              className={styles.ringProgress}
              strokeDasharray={RING_CIRCUMFERENCE}
              strokeDashoffset={dashOffset}
              transform="rotate(-90 26 26)"
            />
          </svg>
          <span className={styles.ringLabel}>{secondsLeft}</span>
        </div>
      </div>

      <div className={styles.route}>
        <div className={styles.routeLine}>
          <span className={styles.dotOrigin} />
          <span className={styles.routeText}>{order?.origin_address ?? "Yuk ortish nuqtasi"}</span>
        </div>
        <span className={styles.routeConnector} />
        <div className={styles.routeLine}>
          <span className={styles.dotDest} />
          <span className={styles.routeText}>{order?.destination_address ?? "Yetkazish nuqtasi"}</span>
        </div>
      </div>

      <div className={styles.metaRow}>
        {order && (
          <span className={styles.metaChip}>
            <WeightIcon color="rgba(255,255,255,0.85)" /> {order.weight} t
          </span>
        )}
        {attempt.distance_km != null && (
          <span className={styles.metaChip}>≈ {Math.round(attempt.distance_km)} km</span>
        )}
        <span className={styles.metaChip}>Navbat #{attempt.round_number}</span>
      </div>

      <div className={styles.priceRow}>
        <span className={styles.priceLabel}>{order?.cargo_name ?? 'Yuk'}</span>
        {order && (
          <span className={styles.price}>
            {formatPrice(order.price)} <span className={styles.currency}>{order.currency}</span>
          </span>
        )}
      </div>

      <div className={styles.actions}>
        <button className={styles.rejectBtn} onClick={onReject} disabled={Boolean(busy)}>
          <CloseIcon color="var(--color-gray-700)" />
          {busy === 'reject' ? '...' : 'Rad etish'}
        </button>
        <button className={styles.acceptBtn} onClick={onAccept} disabled={Boolean(busy)}>
          <CheckIcon color="#fff" />
          {busy === 'accept' ? 'Qabul qilinmoqda...' : 'Qabul qilish'}
        </button>
      </div>
    </div>
  );
}
