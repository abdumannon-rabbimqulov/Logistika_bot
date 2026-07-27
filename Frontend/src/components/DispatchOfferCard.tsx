import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { DispatchAttemptResponse } from '../types/api';
import { formatPrice } from '../utils/format';
import { CheckIcon, CloseIcon, RouteIcon, WeightIcon } from './icons';
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

/** Barmoq shu masofadan ko'p surilsa — bosish emas, tortish (drag) deb hisoblanadi. */
const TAP_SLOP_PX = 6;

/** Navbat bilan kelgan taklif — 60 soniyalik countdown halqa bilan, pastdan chiquvchi
 *  "bottom sheet" ko'rinishida. Haydovchi kartani pastga tortib (yoki sarlavhasiga bosib)
 *  kichraytirishi va xaritadagi marshrutni to'liq ko'rishi mumkin; tepaga tortsa qaytadi. */
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

  // ── Bottom sheet holati ───────────────────────────────────────────────────
  // Yig'ish translateY bilan emas, tana (body) balandligini qisqartirish bilan
  // amalga oshiriladi: shunda sheet doim ekran pastiga "yopishib" turadi va
  // yig'ilganda pastki menyu ustiga chiqib ketmaydi.
  const bodyInnerRef = useRef<HTMLDivElement>(null);
  const [collapsed, setCollapsed] = useState(false);
  // Tananing to'liq (tabiiy) balandligi — ayni paytda yig'ish uchun maksimal siljish.
  const [collapsedOffset, setCollapsedOffset] = useState(0);
  // Pointer hodisalari ichida eng so'nggi qiymat kerak (state closure'da eskirib qoladi).
  const collapsedOffsetRef = useRef(0);
  // Barmoq bilan tortilayotgan paytdagi joriy siljish (null — tortilmayapti).
  const [dragOffset, setDragOffset] = useState<number | null>(null);
  const dragRef = useRef<{ startY: number; baseOffset: number; moved: boolean; offset: number } | null>(null);

  // Tana balandligi o'lchanadi. Kontent o'zgarganda (manzil uzunligi, matn qatorlari)
  // qayta o'lchanishi uchun ResizeObserver — o'lchov cheklanmagan ichki elementda,
  // aks holda tortish paytidagi har bir kadr o'zini qayta o'lchashga sabab bo'lardi.
  useLayoutEffect(() => {
    const inner = bodyInnerRef.current;
    if (!inner) return;
    const measure = () => {
      const next = inner.offsetHeight;
      collapsedOffsetRef.current = next;
      setCollapsedOffset(next);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(inner);
    return () => observer.disconnect();
  }, []);

  // Yangi taklif kelsa sheet doim ochiq holatda ko'rsatiladi.
  useEffect(() => {
    setCollapsed(false);
  }, [attempt.id]);

  const handlePointerDown = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      dragRef.current = {
        startY: event.clientY,
        baseOffset: collapsed ? collapsedOffset : 0,
        moved: false,
        offset: collapsed ? collapsedOffset : 0,
      };
      event.currentTarget.setPointerCapture(event.pointerId);
    },
    [collapsed, collapsedOffset],
  );

  const handlePointerMove = useCallback((event: React.PointerEvent<HTMLDivElement>) => {
    const drag = dragRef.current;
    if (!drag) return;
    const delta = event.clientY - drag.startY;
    if (!drag.moved && Math.abs(delta) < TAP_SLOP_PX) return;
    drag.moved = true;
    // Siljish 0 (to'liq ochiq) va collapsedOffset (yig'ilgan) orasida ushlanadi —
    // sheet ekrandan tashqariga chiqib ketmasligi yoki tepaga "uchib" ketmasligi uchun.
    drag.offset = Math.min(Math.max(drag.baseOffset + delta, 0), collapsedOffsetRef.current);
    setDragOffset(drag.offset);
  }, []);

  const handlePointerUp = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      const drag = dragRef.current;
      dragRef.current = null;
      // pointercancel'dan keyin capture allaqachon bekor qilingan bo'lishi mumkin.
      if (event.currentTarget.hasPointerCapture(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
      if (!drag) return;

      if (!drag.moved) {
        // Tortilmadi — oddiy bosish: holatni teskarisiga o'zgartiradi.
        setCollapsed((prev) => !prev);
        setDragOffset(null);
        return;
      }
      // Yarim yo'ldan oshgan tomonga "yopishadi".
      setCollapsed(drag.offset > collapsedOffsetRef.current / 2);
      setDragOffset(null);
    },
    [],
  );

  const secondsLeft = Math.ceil(remainingMs / 1000);
  const fraction = Math.max(0, Math.min(1, remainingMs / totalMs));
  const dashOffset = RING_CIRCUMFERENCE * (1 - fraction);

  const order = attempt.order;
  const matchLabel = attempt.match_type === 'gps' ? 'Sizga eng yaqin' : 'Sizning hududingizda';

  const offset = dragOffset ?? (collapsed ? collapsedOffset : 0);

  return (
    <div className={styles.sheet} role="dialog" aria-label="Yangi buyurtma taklifi">
      {/* Doim ko'rinadigan qism: tortish dastagi + qisqa xulosa. Yig'ilganda faqat shu qoladi. */}
      <div
        className={styles.peek}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerUp}
        role="button"
        tabIndex={0}
        aria-expanded={!collapsed}
        aria-label={collapsed ? 'Buyurtma kartasini ochish' : 'Buyurtma kartasini yig‘ish'}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setCollapsed((prev) => !prev);
          }
        }}
      >
        <span className={styles.dragHandle} />
        <div className={styles.header}>
          <div className={styles.headerText}>
            <div className={styles.kicker}>Yangi buyurtma</div>
            <div className={styles.match}>{collapsed ? (order?.cargo_name ?? 'Yuk') : matchLabel}</div>
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
      </div>

      <div
        className={styles.bodyClip}
        style={{
          height: Math.max(0, collapsedOffset - offset),
          // Barmoq ostida animatsiya bo'lmasligi kerak — aks holda harakat "kechikadi".
          transition: dragOffset === null ? undefined : 'none',
        }}
        // Yig'ilganda ichkaridagi tugmalar ko'rinmaydi — ular klaviatura/skrinrider
        // uchun ham "yo'q" bo'lishi kerak, aks holda ko'rinmas tugmaga fokus tushadi.
        inert={collapsed}
      >
        <div ref={bodyInnerRef} className={styles.body}>
          <div className={styles.route}>
            <div className={styles.routeLine}>
              <span className={styles.dotOrigin} />
              <span className={styles.routeText}>{order?.origin_address ?? 'Yuk ortish nuqtasi'}</span>
            </div>
            <span className={styles.routeConnector} />
            <div className={styles.routeLine}>
              <span className={styles.dotDest} />
              <span className={styles.routeText}>{order?.destination_address ?? 'Yetkazish nuqtasi'}</span>
            </div>
          </div>

          <div className={styles.metaRow}>
            {/* Marshrut uzunligi (A→B) — buyurtmaning o'z masofasi. */}
            {order?.total_distance_km != null && (
              <span className={styles.metaChip}>
                <RouteIcon color="rgba(255,255,255,0.85)" /> {Math.round(order.total_distance_km)} km
              </span>
            )}
            {order && (
              <span className={styles.metaChip}>
                <WeightIcon color="rgba(255,255,255,0.85)" /> {order.weight} t
              </span>
            )}
            {/* Haydovchidan yuk ortish nuqtasigacha — yuqoridagi marshrut masofasidan
                farqlanishi uchun "Sizgacha" deb aniq belgilanadi. */}
            {attempt.distance_km != null && (
              <span className={styles.metaChip}>Sizgacha ≈ {Math.round(attempt.distance_km)} km</span>
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
      </div>
    </div>
  );
}
