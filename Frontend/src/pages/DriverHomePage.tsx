import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { updateDriverAvailability } from '../api/drivers';
import { acceptDispatch, getActiveDispatch, listMyOrders, rejectDispatch } from '../api/orders';
import { DispatchOfferCard } from '../components/DispatchOfferCard';
import { DriverBottomNav } from '../components/DriverBottomNav';
import { GoOnlineSheet, type GoOnlineResult } from '../components/GoOnlineSheet';
import { ChevronRightIcon } from '../components/icons';
import type { DispatchAttemptResponse, OrderListItem } from '../types/api';
import { formatPrice, statusLabel } from '../utils/format';
import { useDriverCabinet } from './DriverCabinetContext';
import styles from './DriverHomePage.module.css';

const DISPATCH_POLL_MS = 3000;
const ACTIVE_STATUSES = new Set(['ACCEPTED', 'IN_PROGRESS']);

function formatAvailableFrom(dateIso: string): string {
  return new Date(dateIso).toLocaleDateString('uz-UZ', { day: 'numeric', month: 'long' });
}

export function DriverHomePage() {
  const navigate = useNavigate();
  const { cabinet, setCabinet } = useDriverCabinet();

  const [sheetOpen, setSheetOpen] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [attempt, setAttempt] = useState<DispatchAttemptResponse | null>(null);
  const [offerBusy, setOfferBusy] = useState<'accept' | 'reject' | null>(null);
  const [activeOrder, setActiveOrder] = useState<OrderListItem | null>(null);

  const busyRef = useRef(false);
  const pollingRef = useRef(false);

  // Faol (ACCEPTED/IN_PROGRESS) buyurtmani aniqlash — bosh sahifada tez o'tish uchun.
  const loadActiveOrder = useCallback(async () => {
    try {
      const orders = await listMyOrders();
      setActiveOrder(orders.find((o) => ACTIVE_STATUSES.has(o.status)) ?? null);
    } catch {
      // ro'yxat yuklanmasa ham qolgan UI ishlaydi
    }
  }, []);

  useEffect(() => {
    void loadActiveOrder();
  }, [loadActiveOrder]);

  // Liniyada bo'lsa har 3 soniyada faol taklifni tekshiramiz (bot bilan sinxron).
  useEffect(() => {
    if (!cabinet.is_available) {
      setAttempt(null);
      return;
    }
    let cancelled = false;

    const poll = async () => {
      if (busyRef.current || pollingRef.current) return;
      pollingRef.current = true;
      try {
        const next = await getActiveDispatch();
        // Qo'shimcha himoya: backend endi muddati o'tgan taklifni qaytarmaydi
        // (services/dispatch.py get_active_attempt), lekin soatlar farqi yoki kechikkan
        // javob sabab o'tib ketgani kelsa — kartani ko'rsatmaymiz (0 soniyalik miltillash).
        const fresh = next && new Date(next.expires_at).getTime() > Date.now() ? next : null;
        if (!cancelled && !busyRef.current) setAttempt(fresh);
      } catch {
        // jim — keyingi urinishda qayta so'raladi
      } finally {
        pollingRef.current = false;
      }
    };

    void poll();
    const id = window.setInterval(poll, DISPATCH_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [cabinet.is_available]);

  async function handleGoOnline(result: GoOnlineResult) {
    setToggling(true);
    setError(null);
    try {
      const updated = await updateDriverAvailability({
        is_available: true,
        current_city: result.currentCity,
        current_region: result.currentRegion,
        available_from_date: result.availableFromDate,
      });
      setCabinet(updated);
      setSheetOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "O'zgartirib bo'lmadi");
    } finally {
      setToggling(false);
    }
  }

  async function handleGoOffline() {
    setToggling(true);
    setError(null);
    try {
      const updated = await updateDriverAvailability({ is_available: false, available_from_date: null });
      setCabinet(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "O'zgartirib bo'lmadi");
    } finally {
      setToggling(false);
    }
  }

  async function handleAccept() {
    if (!attempt) return;
    busyRef.current = true;
    setOfferBusy('accept');
    setError(null);
    try {
      const order = await acceptDispatch(attempt.id);
      setAttempt(null);
      navigate(`/active/${order.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Qabul qilib bo'lmadi — taklif eskirgan bo'lishi mumkin");
      setAttempt(null);
    } finally {
      busyRef.current = false;
      setOfferBusy(null);
    }
  }

  async function handleReject() {
    if (!attempt) return;
    busyRef.current = true;
    setOfferBusy('reject');
    setError(null);
    try {
      await rejectDispatch(attempt.id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Rad etib bo'lmadi");
    } finally {
      setAttempt(null);
      busyRef.current = false;
      setOfferBusy(null);
    }
  }

  const isFutureAvailability =
    Boolean(cabinet.available_from_date) && new Date(cabinet.available_from_date!) > new Date();

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <div className={styles.header}>
          <div>
            <div className={styles.hello}>Salom,</div>
            <div className={styles.name}>{cabinet.name}</div>
          </div>
          <div className={cabinet.is_available ? styles.statusOnline : styles.statusOffline}>
            <span className={styles.statusDot} />
            {cabinet.is_available ? 'Liniyada' : 'Oflayn'}
          </div>
        </div>

        <div className={styles.balanceCard}>
          <span className={styles.balanceLabel}>Balans</span>
          <span className={styles.balanceValue}>
            {formatPrice(cabinet.balance_amount)} <span className={styles.balanceCurrency}>{cabinet.currency}</span>
          </span>
          <div className={styles.truck}>
            {cabinet.truck_type_name ?? ''} · {cabinet.truck_number}
            {cabinet.truck_year ? ` · ${cabinet.truck_year}` : ''}
          </div>
        </div>

        {attempt && (
          <div className={styles.section}>
            <DispatchOfferCard
              attempt={attempt}
              onAccept={handleAccept}
              onReject={handleReject}
              onExpire={() => setAttempt(null)}
              busy={offerBusy}
            />
          </div>
        )}

        {activeOrder && (
          <button className={styles.activeCard} onClick={() => navigate(`/active/${activeOrder.id}`)}>
            <div className={styles.activeInfo}>
              <div className={styles.activeStatus}>
                <span className={styles.activeDot} />
                {statusLabel(activeOrder.status)}
              </div>
              <div className={styles.activeCargo}>{activeOrder.cargo_name}</div>
              <div className={styles.activeMeta}>{formatPrice(activeOrder.price)} {activeOrder.currency}</div>
            </div>
            <ChevronRightIcon color="#fff" />
          </button>
        )}

        {cabinet.is_blocked ? (
          <div className={styles.blockedBanner}>
            Siz bloklangansiz — liniyaga chiqa olmaysiz. Sabab uchun administratsiyaga murojaat qiling.
          </div>
        ) : (
          <div className={styles.availabilityRow}>
            <div>
              <div className={styles.availabilityText}>Liniyaga chiqish</div>
              <div className={styles.availabilityHint}>
                {!cabinet.is_available && "O'chirilgan — buyurtma takliflari kelmaydi"}
                {cabinet.is_available && !isFutureAvailability && 'Yoqilgan — takliflarni qabul qilyapsiz'}
                {cabinet.is_available && isFutureAvailability &&
                  `${formatAvailableFrom(cabinet.available_from_date!)} dan yuk qabul qilasiz`}
              </div>
            </div>
            <button
              className={cabinet.is_available ? styles.switchOn : styles.switch}
              onClick={() => (cabinet.is_available ? handleGoOffline() : setSheetOpen(true))}
              disabled={toggling}
              aria-label="Liniyaga chiqish"
            >
              <span className={cabinet.is_available ? styles.switchKnobOn : styles.switchKnob} />
            </button>
          </div>
        )}

        {error && <div className={styles.errorBanner}>{error}</div>}

        {!attempt && cabinet.is_available && !activeOrder && (
          <div className={styles.waiting}>
            <div className={styles.waitingPulse} />
            <div className={styles.waitingText}>Buyurtma qidirilmoqda...</div>
            <div className={styles.waitingHint}>Sizga mos yuk topilishi bilan bu yerda taklif chiqadi.</div>
          </div>
        )}
      </div>

      {sheetOpen && (
        <GoOnlineSheet onSubmit={handleGoOnline} onClose={() => setSheetOpen(false)} submitting={toggling} />
      )}
      <DriverBottomNav />
    </div>
  );
}
