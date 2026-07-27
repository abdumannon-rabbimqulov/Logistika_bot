import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApiError } from '../api/client';
import { updateDriverAvailability } from '../api/drivers';
import { acceptDispatch, getActiveDispatch, listMyOrders, rejectDispatch } from '../api/orders';
import { DispatchOfferCard } from '../components/DispatchOfferCard';
import { DriverBottomNav } from '../components/DriverBottomNav';
import { GoOnlineSheet, type GoOnlineResult } from '../components/GoOnlineSheet';
import { YandexMap } from '../components/YandexMap';
import { ChevronRightIcon, PowerIcon } from '../components/icons';
import { useLiveLocation } from '../hooks/useLiveLocation';
import type { DispatchAttemptResponse, OrderListItem } from '../types/api';
import { formatPrice, statusLabel } from '../utils/format';
import { useDriverCabinet } from './DriverCabinetContext';
import styles from './DriverHomePage.module.css';

const DISPATCH_POLL_MS = 3000;
const ACTIVE_STATUSES = new Set(['SCHEDULED', 'ACCEPTED', 'IN_PROGRESS']);

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

  // Jonli joylashuv: xaritadagi ko'k nuqta. Liniyadagi holatda koordinata
  // `/drivers/ws/location` orqali backendga ham uzatiladi (admin jonli xaritasi).
  const { coords, error: geoError } = useLiveLocation({ broadcast: cabinet.is_available });

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
        // `current_region` faqat kiritilgan bo'lsa yuboriladi — backend `exclude_unset`
        // bilan ishlaydi, shuning uchun bo'sh qiymat eski qiymatni o'chirmaydi.
        ...(result.currentRegion ? { current_region: result.currentRegion } : {}),
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

  const onlineHint = !cabinet.is_available
    ? "O'chirilgan — buyurtma takliflari kelmaydi"
    : isFutureAvailability
      ? `${formatAvailableFrom(cabinet.available_from_date!)} dan yuk qabul qilasiz`
      : 'Yoqilgan — takliflarni qabul qilyapsiz';

  // Taklif kelganda xaritada A/B nuqtalari va OSRM marshrut chizig'i ko'rsatiladi —
  // haydovchi qabul qilishdan oldin yo'nalishni ko'z bilan baholay olishi uchun.
  // (Koordinatalar bo'lmasa `undefined` beriladi va xarita odatdagidek haydovchini kuzatadi.)
  const offer = attempt?.order;
  const offerOrigin =
    offer?.origin_latitude != null && offer.origin_longitude != null
      ? { latitude: offer.origin_latitude, longitude: offer.origin_longitude }
      : null;
  const offerDestination =
    offer?.destination_latitude != null && offer.destination_longitude != null
      ? { latitude: offer.destination_latitude, longitude: offer.destination_longitude }
      : null;

  return (
    <div className={styles.page}>
      {/* Bosh sahifa — xarita. Qolgan hamma narsa uning ustida "suzadi". */}
      <div className={styles.mapLayer}>
        <YandexMap
          origin={offerOrigin}
          destination={offerDestination}
          route={offer?.route_geometry?.length ? offer.route_geometry : null}
          userLocation={coords}
          followUser
        />
      </div>

      {/* Yuqori qatlam: "liniyaga chiqish" power tugmasi (chapda) + holat chipi */}
      <div className={styles.topBar}>
        <button
          className={cabinet.is_available ? styles.powerBtnOn : styles.powerBtnOff}
          onClick={() => (cabinet.is_available ? handleGoOffline() : setSheetOpen(true))}
          disabled={toggling || cabinet.is_blocked}
          aria-pressed={cabinet.is_available}
          aria-label={cabinet.is_available ? 'Liniyadan chiqish' : 'Liniyaga chiqish'}
          title={onlineHint}
        >
          <PowerIcon size={24} color="#fff" />
        </button>
        <div className={styles.topInfo}>
          <div className={cabinet.is_available ? styles.statusOnline : styles.statusOffline}>
            <span className={styles.statusDot} />
            {cabinet.is_available ? 'Liniyada' : 'Oflayn'}
          </div>
          {!coords && <div className={styles.geoChip}>Joylashuv aniqlanmoqda...</div>}
        </div>
      </div>

      {/* Pastki suzuvchi qatlam: taklif / faol buyurtma / liniyaga chiqish */}
      <div className={styles.floatLayer}>
        {geoError && <div className={styles.geoWarn}>{geoError}</div>}
        {error && <div className={styles.errorBanner}>{error}</div>}

        {activeOrder && !attempt && (
          <button className={styles.activeCard} onClick={() => navigate(`/active/${activeOrder.id}`)}>
            <div className={styles.activeInfo}>
              <div className={styles.activeStatus}>
                <span className={styles.activeDot} />
                {statusLabel(activeOrder.status)}
              </div>
              <div className={styles.activeCargo}>{activeOrder.cargo_name}</div>
              <div className={styles.activeMeta}>
                {formatPrice(activeOrder.price)} {activeOrder.currency}
              </div>
            </div>
            <ChevronRightIcon color="#fff" />
          </button>
        )}

        {!attempt && cabinet.is_available && !activeOrder && (
          <div className={styles.searching}>
            <span className={styles.searchingPulse} />
            Buyurtma qidirilmoqda...
          </div>
        )}

        {cabinet.is_blocked && (
          <div className={styles.blockedBanner}>
            Siz bloklangansiz — liniyaga chiqa olmaysiz. Sabab uchun administratsiyaga murojaat qiling.
          </div>
        )}

        {/* Holat matni — power tugmasi nima qilishini so'z bilan tushuntiradi. */}
        {!cabinet.is_blocked && !attempt && <div className={styles.hintChip}>{onlineHint}</div>}
      </div>

      {/* Taklif — xaritani bosib qolmaslik uchun pastdan chiquvchi, tortiladigan sheet.
          `floatLayer` ichida emas, alohida qatlamda: u ekran pastiga "yopishib" turadi. */}
      {attempt && (
        <DispatchOfferCard
          attempt={attempt}
          onAccept={handleAccept}
          onReject={handleReject}
          onExpire={() => setAttempt(null)}
          busy={offerBusy}
        />
      )}

      {sheetOpen && (
        <GoOnlineSheet onSubmit={handleGoOnline} onClose={() => setSheetOpen(false)} submitting={toggling} />
      )}
      <DriverBottomNav />
    </div>
  );
}
