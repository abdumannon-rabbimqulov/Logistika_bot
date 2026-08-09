import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ApiError, type ApiProblem } from '../api/client';
import { getOrder, updateWaypoint } from '../api/orders';
import { BackIcon, ClockIcon, PhoneIcon, RouteIcon, SendIcon, WeightIcon } from '../components/icons';
import { OrderRouteMap } from '../components/OrderRouteMap';
import { useLiveLocation } from '../hooks/useLiveLocation';
import type { OrderDetail, OrderWaypoint, WaypointStatus, WaypointType } from '../types/api';
import { getCurrentPositionOnce, PositionError } from '../utils/currentPosition';
import { openTelegramLocationSettings } from '../utils/telegramLocation';
import { formatPrice, statusLabel, unloadingLabel } from '../utils/format';
import { describePickupAt } from '../utils/pickupTime';
import { buildYandexPointUrl, buildYandexRouteUrl } from '../utils/yandexRoute';
import styles from './DriverActiveOrderPage.module.css';

const WAYPOINT_TYPE_LABEL: Record<WaypointType, string> = {
  PICKUP: 'Yuk ortish',
  DELIVERY: 'Yetkazish',
  TRANSIT: 'Oraliq nuqta',
};

/** Joriy nuqtadagi keyingi qadam: tugma matni va nuqtaning yangi holati.
 *
 *  Ilgari bu yerda buyurtma statusiga bog'langan ikkita tugma bor edi
 *  (`ACCEPTED → IN_PROGRESS → COMPLETED`) va ular oraliq nuqtalarni umuman
 *  hisobga olmasdi. Endi qadam har doim JORIY nuqtaga tegishli, shuning uchun
 *  2 ta ham, 5 ta ham nuqtali marshrut bir xil ishlaydi. */
function nextStep(
  waypoint: OrderWaypoint,
): { label: string; status: WaypointStatus } | null {
  if (waypoint.status === 'PENDING') return { label: 'Yetib keldim', status: 'ARRIVED' };
  if (waypoint.status === 'ARRIVED') {
    const label =
      waypoint.type === 'PICKUP'
        ? 'Yukni ortdim'
        : waypoint.type === 'DELIVERY'
          ? 'Yukni topshirdim'
          : 'Nuqtani yakunladim';
    return { label, status: 'COMPLETED' };
  }
  return null;
}

function contactOf(order: OrderDetail): OrderWaypoint | null {
  const pickup = order.waypoints.find((w) => w.type === 'PICKUP' && w.contact_phone);
  return pickup ?? order.waypoints.find((w) => w.contact_phone) ?? order.origin ?? null;
}

/** Buyurtmadagi birinchi tugallanmagan nuqta — backenddagi `Order.current_waypoint`
 *  bilan bir xil qoida. Backend `current_waypoint`ni javobda bersa ham, ro'yxatdagi
 *  aynan shu obyektni topish qulayroq (id bo'yicha solishtirish uchun). */
function currentWaypointOf(order: OrderDetail): OrderWaypoint | null {
  return order.waypoints.find((w) => w.status !== 'COMPLETED' && w.status !== 'SKIPPED') ?? null;
}

/** Nuqta yakunlanganmi (o'tib bo'lingan). */
function isWaypointDone(waypoint: OrderWaypoint): boolean {
  return waypoint.status === 'COMPLETED' || waypoint.status === 'SKIPPED';
}

/**
 * Nuqtagacha "Yo'l ko'rsat" havolasi (Yandex Maps / Navigator).
 *
 * Boshlanish nuqtasi uchun zaxira zanjiri:
 *   1. haydovchining JORIY joylashuvi — eng foydalisi, "shu yerdan borish"
 *   2. joylashuv yo'q bo'lsa (ruxsat berilmagan) — oldingi nuqta, ya'ni marshrutning
 *      shu bo'lagi ko'rinadi
 *   3. birinchi nuqta bo'lsa boshlanish yo'q — marshrut o'rniga NUQTANING O'ZI
 *      xaritada ochiladi (`buildYandexPointUrl`), haydovchi navigatsiyani Yandex
 *      ichida boshlaydi
 *
 * Nima uchun imkon boricha marshrut: haydovchiga "qayerda" emas, "qanday borish"
 * kerak — marshrutli havola telefonda darhol navigatsiyani boshlaydi.
 */
function navigationUrlFor(
  order: OrderDetail,
  waypoint: OrderWaypoint,
  driverCoords: { latitude: number; longitude: number } | null,
): string | null {
  const index = order.waypoints.indexOf(waypoint);
  const previous = index > 0 ? order.waypoints[index - 1] : null;
  const start = driverCoords ?? previous;
  // `start` yo'q bo'lsa marshrut qurib bo'lmaydi. `buildYandexRouteUrl` boshlanish
  // va tugash bir xil bo'lgan holatni ham o'zi nuqta havolasiga aylantiradi.
  return start ? buildYandexRouteUrl(start, waypoint) : buildYandexPointUrl(waypoint);
}

export function DriverActiveOrderPage() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // Backend bir so'rovga bir nechta sabab qaytarishi mumkin (services/problems.py).
  const [problems, setProblems] = useState<ApiProblem[]>([]);
  const [showLocationSettingsHint, setShowLocationSettingsHint] = useState(false);
  const [updating, setUpdating] = useState(false);

  // Faol buyurtma davomida joylashuv uzatiladi — mijoz kuzatuv sahifasida va admin
  // jonli xaritasida haydovchi ko'rinib tursin. Ilgari uzatish faqat bosh sahifada
  // va faqat "liniyada" holatida ishlagan, ya'ni yuk yo'ldaligida umuman to'xtardi.
  const isTracking = Boolean(order && order.status !== 'COMPLETED' && order.status !== 'CANCELLED');
  // `coords` — haydovchining joriy joylashuvi. Ilgari hook'ning qaytargan qiymati
  // tashlab yuborilardi (faqat uzatish uchun chaqirilgan edi); endi u ikki joyda
  // ishlatiladi: xaritadagi "men" nuqtasi va "Yo'l ko'rsat" havolasining boshlanishi.
  const { coords } = useLiveLocation({ broadcast: isTracking });

  const load = useCallback(async () => {
    if (!orderId) return;
    try {
      const detail = await getOrder(Number(orderId));
      setOrder(detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Buyurtma yuklanmadi');
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleAdvance() {
    if (!order) return;
    const waypoint = currentWaypointOf(order);
    const step = waypoint && nextStep(waypoint);
    if (!waypoint || !step) return;

    setUpdating(true);
    setError(null);
    setProblems([]);
    setShowLocationSettingsHint(false);
    try {
      // Qadam tasdiqlanishidan oldin aynan shu lahzadagi joylashuv olinadi — server
      // shu koordinata bo'yicha haydovchi nuqtada ekanini tekshiradi (geofence).
      const position = await getCurrentPositionOnce();
      const updated = await updateWaypoint(order.id, waypoint.id, {
        status: step.status,
        latitude: position.latitude,
        longitude: position.longitude,
        ...(position.accuracy != null ? { accuracy: position.accuracy } : {}),
      });
      setOrder(updated);
    } catch (err) {
      if (err instanceof PositionError) {
        setError(err.message);
        setShowLocationSettingsHint(err.canOpenSettings);
      } else if (err instanceof ApiError) {
        setError(err.message);
        setProblems(err.problems);
        // Joylashuv aniqlanmagan bo'lsa — sozlamalar tugmasi ham foydali bo'ladi.
        setShowLocationSettingsHint(err.problems.some((p) => p.code === 'LOCATION_UNKNOWN'));
      } else {
        setError("Qadamni belgilab bo'lmadi");
      }
    } finally {
      setUpdating(false);
    }
  }

  if (loading) {
    return (
      <div className={styles.center}>
        <div className={styles.spinner} />
      </div>
    );
  }

  if (!order) {
    return (
      <div className={styles.center}>
        <div className={styles.errorBanner}>{error ?? 'Buyurtma topilmadi'}</div>
        <button className={styles.backLink} onClick={() => navigate('/')}>Bosh sahifaga</button>
      </div>
    );
  }

  const contact = contactOf(order);
  const currentWaypoint = currentWaypointOf(order);
  const step = currentWaypoint ? nextStep(currentWaypoint) : null;
  const isDone = order.status === 'COMPLETED';
  const isCancelled = order.status === 'CANCELLED';

  // Xarita uchun koordinatalar. `OrderRouteMap` `{latitude, longitude}` kutadi,
  // waypoint'da esa ular `null` bo'lishi mumkin (manzil qo'lda kiritilgan bo'lsa).
  const mapOrigin =
    order.origin?.latitude != null && order.origin.longitude != null
      ? { latitude: order.origin.latitude, longitude: order.origin.longitude }
      : null;
  const mapDestination =
    order.destination?.latitude != null && order.destination.longitude != null
      ? { latitude: order.destination.latitude, longitude: order.destination.longitude }
      : null;

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <div className={styles.topBar}>
          <button className={styles.iconBtn} onClick={() => navigate('/')} aria-label="Orqaga">
            <BackIcon />
          </button>
          {/* Buyurtma raqami — haydovchi qo'llab-quvvatlash xizmatiga yozganda yoki
              nizo bo'lganda aynan shu raqamni aytadi. Ilgari ekranda umuman yo'q edi. */}
          <div className={styles.topTitle}>Buyurtma #{order.id}</div>
          <div className={styles.statusPill}>{statusLabel(order.status)}</div>
        </div>

        {/* Marshrut xaritasi — ilgari haydovchi faqat manzil MATNINI ko'rardi.
            Sender sahifasidan farqli o'laroq bu yerda xarita fon emas: sahifa
            aylanadi, shuning uchun xarita belgilangan balandlikdagi blok
            (`.mapCard`) ichida. Koordinata bo'lmasa umuman ko'rsatilmaydi. */}
        {mapOrigin && (
          <div className={styles.mapCard}>
            <OrderRouteMap
              origin={mapOrigin}
              destination={mapDestination}
              driverLocation={coords}
            />
          </div>
        )}

        {/* Mashina sig'imidan oshgani — buyurtmani yaratishda hisoblanadi
            (`overload_warning`). Haydovchi yo'lga chiqishdan OLDIN bilishi kerak:
            ortiqcha yuk bilan yo'l nazoratida muammo bo'ladi. */}
        {order.overload_warning && (
          <div className={styles.warningBanner}>{order.overload_warning}</div>
        )}

        <div className={styles.cargoCard}>
          <div className={styles.cargoName}>{order.cargo_name}</div>
          <div className={styles.cargoMeta}>
            <span className={styles.metaChip}><WeightIcon /> {order.weight} t</span>
            {/* Hajm — og'irlik yetarli bo'lsa ham yuk kuzovga sig'masligi mumkin. */}
            {order.volume != null && (
              <span className={styles.metaChip}>{order.volume} m³</span>
            )}
            {order.total_distance_km != null && (
              <span className={styles.metaChip}>≈ {Math.round(order.total_distance_km)} km</span>
            )}
            {/* Tushirish sharti — haydovchi uchun reysdan keyin mashina qancha band
                bo'lishini bildiradi (mijoz tanlamagan bo'lsa ko'rsatilmaydi). */}
            {unloadingLabel(order.unloading_mode, order.unloading_wait_hours) && (
              <span className={styles.metaChip}>
                {unloadingLabel(order.unloading_mode, order.unloading_wait_hours)}
              </span>
            )}
          </div>
          {/* Yuk ortish vaqti — haydovchi uchun eng muhim ma'lumot va shu paytgacha
              ekranda UMUMAN yo'q edi. `describePickupAt` "Bugun 14:30" / "Ertaga
              09:00" ko'rinishida beradi (utils/pickupTime.ts) — sana o'rniga shu
              yozuv bir qarashda tushunarli. */}
          <div className={styles.timeRow}>
            <ClockIcon size={15} color="var(--color-accent-pressed)" />
            <span className={styles.timeLabel}>Yuk ortish</span>
            <span className={styles.timeValue}>
              {describePickupAt(new Date(order.pickup_at))}
            </span>
          </div>

          {/* Jo'nash vaqti odatda yuk ortish vaqti bilan bir xil; farq qilgandagina
              ko'rsatiladi, aks holda bir xil vaqt ikki marta yozilib chalkashtirardi. */}
          {order.departure_at && order.departure_at !== order.pickup_at && (
            <div className={styles.timeRow}>
              <RouteIcon size={15} color="var(--color-text-secondary)" />
              <span className={styles.timeLabel}>Jo'nash</span>
              <span className={styles.timeValue}>
                {describePickupAt(new Date(order.departure_at))}
              </span>
            </div>
          )}

          <div className={styles.priceRow}>
            <span className={styles.priceLabel}>To'lov</span>
            <span className={styles.price}>{formatPrice(order.price)} {order.currency}</span>
          </div>
        </div>

        <div className={styles.sectionTitle}>Marshrut</div>
        <div className={styles.route}>
          {order.waypoints.map((wp, idx) => {
            const isLast = idx === order.waypoints.length - 1;
            const isCurrent = currentWaypoint?.id === wp.id;
            return (
              <div key={wp.id} className={styles.checkpoint}>
                <div className={styles.markerCol}>
                  <span className={`${styles.marker} ${styles[`marker_${wp.status}`] ?? ''}`} />
                  {!isLast && <span className={styles.connector} />}
                </div>
                <div className={styles.checkpointBody}>
                  <div className={styles.checkpointType}>
                    {WAYPOINT_TYPE_LABEL[wp.type]}
                    {isCurrent && !isDone && !isCancelled && (
                      <span className={styles.currentTag}>Joriy nuqta</span>
                    )}
                  </div>
                  <div className={styles.checkpointAddress}>{wp.address ?? 'Manzil ko’rsatilmagan'}</div>

                  <div className={styles.checkpointActions}>
                    {wp.contact_phone && (
                      <a className={styles.miniCall} href={`tel:${wp.contact_phone}`}>
                        <PhoneIcon size={13} color="var(--color-accent-pressed)" /> {wp.contact_name ?? wp.contact_phone}
                      </a>
                    )}
                    {/* "Yo'l ko'rsat" — faqat hali borilmagan nuqtalarda. O'tib
                        bo'lingan nuqtaga navigatsiyaning ma'nosi yo'q va tugmalar
                        ro'yxatni keraksiz to'ldirardi. */}
                    {!isWaypointDone(wp) && !isDone && !isCancelled && (() => {
                      const url = navigationUrlFor(order, wp, coords);
                      if (!url) return null;
                      return (
                        <a
                          className={styles.navBtn}
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <RouteIcon size={13} color="var(--color-accent-pressed)" /> Yo'l ko'rsat
                        </a>
                      );
                    })()}
                  </div>

                  {/* Tasdiqlangan qadamlar: qachon va qanchalik yaqindan belgilangani —
                      haydovchi uchun ham, nizo holatida admin uchun ham ochiq ma'lumot. */}
                  {wp.completed_at && (
                    <div className={styles.checkpointProof}>
                      {new Date(wp.completed_at).toLocaleTimeString('uz-UZ', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                      {wp.confirmed_distance_m != null && ` · nuqtadan ${wp.confirmed_distance_m} m`}
                      {wp.override_reason && ' · admin tasdiqlagan'}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {order.sender_contact && (
          <>
            <div className={styles.sectionTitle}>Buyurtmachi</div>
            <div className={styles.customerCard}>
              <div className={styles.customerInfo}>
                <div className={styles.customerName}>{order.sender_contact.full_name}</div>
                {/* Telefon raqamining O'ZI ham bosiladigan bo'ldi — ilgari faqat
                    yondagi ikonka ishlardi va raqamni bosgan haydovchi hech narsa
                    bo'lmaganidan hayron qolardi. */}
                {order.sender_contact.phone_number ? (
                  <a
                    className={styles.customerPhone}
                    href={`tel:${order.sender_contact.phone_number}`}
                  >
                    {order.sender_contact.phone_number}
                  </a>
                ) : (
                  <div className={styles.customerPhone}>Telefon ko’rsatilmagan</div>
                )}
                {/* Telegram username — ilgari faqat ikonka bor edi, ya'ni haydovchi
                    kimga yozayotganini ko'rmasdi. */}
                {order.sender_contact.username && (
                  <div className={styles.customerUsername}>@{order.sender_contact.username}</div>
                )}
              </div>
              <div className={styles.customerActions}>
                {order.sender_contact.phone_number && (
                  <a
                    className={styles.callBtn}
                    href={`tel:${order.sender_contact.phone_number}`}
                    aria-label="Buyurtmachiga qo'ng'iroq qilish"
                  >
                    <PhoneIcon />
                  </a>
                )}
                {order.sender_contact.telegram_url && (
                  <a
                    className={styles.callBtn}
                    href={order.sender_contact.telegram_url}
                    target="_blank"
                    rel="noreferrer"
                    aria-label="Buyurtmachiga Telegram orqali yozish"
                  >
                    <SendIcon />
                  </a>
                )}
              </div>
            </div>
          </>
        )}

        {/* Yuk ortish/topshirish manzilidagi kontakt (buyurtmachining o'zi emas —
            masalan ombor xodimi) — buyurtmachidan alohida, chunki boshqa odam bo'lishi mumkin. */}
        {contact && (
          <>
            <div className={styles.sectionTitle}>Manzildagi aloqa</div>
            <div className={styles.customerCard}>
              <div className={styles.customerInfo}>
                <div className={styles.customerName}>{contact.contact_name ?? 'Mijoz'}</div>
                <div className={styles.customerPhone}>{contact.contact_phone ?? 'Telefon ko’rsatilmagan'}</div>
              </div>
              {contact.contact_phone && (
                <a className={styles.callBtn} href={`tel:${contact.contact_phone}`} aria-label="Qo'ng'iroq qilish">
                  <PhoneIcon />
                </a>
              )}
            </div>
          </>
        )}

        {error && (
          <div className={styles.errorBanner}>
            {/* Bitta so'rov bir nechta sababdan rad etilishi mumkin (masofa, noto'g'ri
                nuqta, holat) — hammasi alohida qatorda ko'rsatiladi, aks holda ular
                bitta uzun gapga qo'shilib o'qilmay qolardi. */}
            {problems.length > 1 ? (
              <ul className={styles.errorList}>
                {problems.map((problem) => (
                  <li key={problem.code}>{problem.message}</li>
                ))}
              </ul>
            ) : (
              error
            )}
            {showLocationSettingsHint && (
              <button
                type="button"
                className={styles.settingsLink}
                onClick={() => openTelegramLocationSettings()}
              >
                Sozlamalarni ochish
              </button>
            )}
          </div>
        )}
      </div>

      <div className={styles.footer}>
        {isDone ? (
          <div className={styles.doneNote}>Buyurtma yakunlandi ✅</div>
        ) : isCancelled ? (
          <div className={styles.doneNote}>Buyurtma bekor qilingan</div>
        ) : step && currentWaypoint ? (
          <>
            {/* Qadam nuqtaga borib bosilishi kerakligi oldindan aytiladi — haydovchi
                422 xatosini ko'rgandan keyin emas, oldin biladi. */}
            <div className={styles.stepHint}>
              {currentWaypoint.address ?? 'Manzil ko’rsatilmagan'} — joylashuvingiz tekshiriladi
            </div>
            <button className={styles.advanceBtn} onClick={handleAdvance} disabled={updating}>
              {updating ? 'Joylashuv tekshirilmoqda...' : step.label}
            </button>
          </>
        ) : (
          <div className={styles.doneNote}>Barcha nuqtalar yakunlangan</div>
        )}
      </div>
    </div>
  );
}
