import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
// Yon ta'sir importi: `L.Routing` nomlar fazosini `L` ga qo'shadi. Import qatori
// olib tashlansa TypeScript jim turadi (turlar alohida paketda), lekin ish vaqtida
// `L.Routing is undefined` bilan yiqiladi.
import 'leaflet-routing-machine';
import 'leaflet-routing-machine/dist/leaflet-routing-machine.css';
import styles from './OrderRouteMap.module.css';

/**
 * OSRM manzili. Brauzer OSRM'ga TO'G'RIDAN-TO'G'RI bora olmaydi — u compose
 * tarmog'ining ichida (`docker-compose.prod.yml` da tashqi port ochilmagan).
 * Shuning uchun nisbiy `/osrm/...` yo'li ishlatiladi:
 *   • dev  — Vite proxy (vite.config.ts) uni OSRM konteyneriga uzatadi
 *   • prod — nginx (Frontend/nginx.conf) `/osrm/route/v1/driving/...` ni uzatadi
 * Ikkala holatda ham frontend bilan bir xil origin — CORS muammosi yo'q.
 *
 * LRM `serviceUrl` ga `/{profil}/{koordinatalar}` qismini o'zi qo'shadi.
 */
const OSRM_SERVICE_URL = import.meta.env.VITE_OSRM_SERVICE_URL || '/osrm/route/v1';

/** O'zbekiston markazi — koordinatalar hali kelmaganda xarita shu yerdan boshlanadi. */
const UZBEKISTAN_CENTER: L.LatLngTuple = [41.3775, 64.5853];
const UZBEKISTAN_ZOOM = 6;
/** Faqat bitta nuqta bo'lganda (masalan yetkazish manzili yo'q) shu zoom ishlatiladi. */
const SINGLE_POINT_ZOOM = 14;
/** Marshrut sig'dirilganda chetlarda qoladigan bo'sh joy (px). */
const FIT_PADDING: L.PointTuple = [40, 40];

export interface MapPoint {
  latitude: number;
  longitude: number;
}

interface Props {
  /** Yuk ortish nuqtasi. */
  origin?: MapPoint | null;
  /** Yetkazish nuqtasi. */
  destination?: MapPoint | null;
  /** Biriktirilgan haydovchining jonli joylashuvi (WS orqali yangilanadi). */
  driverLocation?: MapPoint | null;
}

function toLatLng(point: MapPoint): L.LatLng {
  return L.latLng(point.latitude, point.longitude);
}

/**
 * LRM Control'ining tugallanmagan OSRM so'rovi. Ommaviy API'da yo'q, shuning uchun
 * shu yerda tor tip bilan e'lon qilinadi.
 */
interface RoutingControlInternals {
  _pendingRequest?: { abort?: () => void } | null;
}

/**
 * Marshrut control'ini XAVFSIZ olib tashlaydi.
 *
 * NEGA KERAK (haqiqiy xato, brauzerda ushlangan):
 * OSRM so'rovi ketayotganda foydalanuvchi sahifadan chiqib ketsa, xarita yo'q
 * qilinadi, so'ng javob kelib LRM `_clearLines()` ni chaqiradi va u endi `null`
 * bo'lgan `this._map.removeLayer(...)` ga murojaat qilib yiqiladi:
 *   TypeError: Cannot read properties of null (reading 'removeLayer')
 *
 * Yechim — control'ni olib tashlashdan OLDIN kutayotgan so'rovni bekor qilish.
 * Bekor qilingan so'rov uchun LRM `err.type === 'abort'` deb hodisa chiqarmaydi,
 * ya'ni yolg'on "marshrut xatosi" ham ko'rsatilmaydi.
 *
 * `_pendingRequest` — LRM'ning ichki maydoni. Kelajakdagi versiyada nomi o'zgarsa
 * `?.` tufayli hech narsa buzilmaydi: shunchaki eski (xatoli) xatti-harakat qaytadi,
 * shuning uchun bu yerda qattiq bog'lanish yo'q.
 */
function destroyRouting(map: L.Map, routing: L.Routing.Control | null): void {
  if (!routing) return;
  (routing as unknown as RoutingControlInternals)._pendingRequest?.abort?.();
  map.removeControl(routing);
}

/** Rangli doira ko'rinishidagi belgi (Leaflet'ning PNG belgisi o'rniga — CSS'dagi izohga qarang). */
function circleIcon(modifierClass: string): L.DivIcon {
  return L.divIcon({
    className: '', // Leaflet standart `leaflet-div-icon` fonini qo'shmasin
    html: `<div class="${styles.marker} ${modifierClass}"></div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  });
}

/**
 * Buyurtma marshrutini ko'rsatuvchi Leaflet xaritasi.
 *
 * Marshrutni Leaflet Routing Machine hisoblaydi: u OSRM'ga so'rov yuboradi va
 * qaytgan geometriyani polyline sifatida o'zi chizadi. Ya'ni chiziqni biz qo'lda
 * chizmaymiz — LRM'ning `lineOptions` i orqali faqat ko'rinishini beramiz.
 *
 * OSRM javob bermasa (xizmat o'chgan, xarita yuklanmagan) — `routingerror`
 * hodisasi ushlanadi va A→B orasida punktir chiziq ko'rsatiladi, shunda
 * foydalanuvchi kamida yo'nalishni tushunadi. Xarita bo'sh qolmaydi.
 */
export function OrderRouteMap({ origin, destination, driverLocation }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const routingRef = useRef<L.Routing.Control | null>(null);
  const markersRef = useRef<L.Marker[]>([]);
  const driverMarkerRef = useRef<L.Marker | null>(null);
  const fallbackLineRef = useRef<L.Polyline | null>(null);
  const [routingFailed, setRoutingFailed] = useState(false);

  // ── 1. Xaritani bir marta yaratish ───────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const map = L.map(containerRef.current, {
      center: UZBEKISTAN_CENTER,
      zoom: UZBEKISTAN_ZOOM,
      // Telefon ekranida ikki barmoq bilan zoom qulayroq; `+/-` tugmalari joy egallaydi.
      zoomControl: false,
    });
    mapRef.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      // OpenStreetMap litsenziyasi (ODbL) manbani ko'rsatishni TALAB qiladi —
      // bu qatorni olib tashlash mumkin emas.
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    // Konteyner o'lchami keyin o'zgarsa (bottom sheet surilishi, klaviatura ochilishi)
    // Leaflet plitkalari eski o'lchamda "qotib" qoladi — invalidateSize buni tuzatadi.
    const resizeObserver = new ResizeObserver(() => map.invalidateSize());
    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
      // Marshrut control'i xarita YO'Q QILINISHIDAN OLDIN olib tashlanadi.
      // React unmount paytida tozalash funksiyalarini e'lon tartibida chaqiradi,
      // ya'ni bu effekt (birinchi) marshrut effektidan oldin ishlaydi — shuning
      // uchun tozalashga shu yerda tayanamiz, quyidagi effektga emas.
      destroyRouting(map, routingRef.current);
      map.remove();
      mapRef.current = null;
      routingRef.current = null;
      markersRef.current = [];
      driverMarkerRef.current = null;
      fallbackLineRef.current = null;
    };
  }, []);

  // ── 2. Marshrut va A/B belgilari ─────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Oldingi holatni tozalash — prop o'zgarganda eski chiziq/belgilar qolib ketmasin.
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = [];
    destroyRouting(map, routingRef.current);
    routingRef.current = null;
    if (fallbackLineRef.current) {
      fallbackLineRef.current.remove();
      fallbackLineRef.current = null;
    }
    setRoutingFailed(false);

    const originLatLng = origin ? toLatLng(origin) : null;
    const destinationLatLng = destination ? toLatLng(destination) : null;

    if (originLatLng) {
      markersRef.current.push(
        L.marker(originLatLng, { icon: circleIcon(styles.markerOrigin), title: 'Yuk ortish' }).addTo(map),
      );
    }
    if (destinationLatLng) {
      markersRef.current.push(
        L.marker(destinationLatLng, { icon: circleIcon(styles.markerDestination), title: 'Yetkazish' }).addTo(map),
      );
    }

    // Bitta nuqta bor, ikkinchisi yo'q — marshrut hisoblab bo'lmaydi, shunchaki
    // bor nuqtaga markazlashamiz.
    if (!originLatLng || !destinationLatLng) {
      const single = originLatLng ?? destinationLatLng;
      if (single) map.setView(single, SINGLE_POINT_ZOOM);
      return;
    }

    const routing = L.Routing.control({
      // Waypoint'lar `plan` orqali beriladi, `waypoints` orqali emas: belgi yasash
      // (`createMarker`) va surish taqiqlari LRM'da aynan Plan'ga tegishli.
      // Bu xarita FAQAT ko'rsatish uchun — foydalanuvchi marshrutni sichqoncha
      // bilan surib o'zgartira olmasligi kerak (manzillar backendda qat'iy).
      plan: L.Routing.plan([originLatLng, destinationLatLng], {
        // Belgilarni yuqorida o'zimiz qo'ydik — LRM o'zinikini qo'shmasin.
        // `false` qaytarish LRM uchun "belgi kerak emas" degani.
        createMarker: () => false,
        addWaypoints: false,
        draggableWaypoints: false,
      }),
      router: L.Routing.osrmv1({
        serviceUrl: OSRM_SERVICE_URL,
        profile: 'driving',
      }),
      // Marshrut chizig'ining ko'rinishi: keng oq "casing" ustida yashil asosiy
      // chiziq — mavjud YandexMap komponentidagi uslub bilan bir xil.
      lineOptions: {
        styles: [
          { color: '#FFFFFF', weight: 9, opacity: 0.9, lineCap: 'round', lineJoin: 'round' },
          { color: '#15803D', weight: 5, opacity: 1, lineCap: 'round', lineJoin: 'round' },
        ],
        // LRM chiziqni waypoint'largacha "cho'zmaydi" — OSRM qaytargan geometriya
        // o'zi to'liq, sun'iy to'g'ri chiziq qo'shilsa xaritada burchak paydo bo'lardi.
        extendToWaypoints: false,
        missingRouteTolerance: 0,
      },
      // Burilishlar ro'yxati paneli kerak emas (CSS'dagi izohga qarang).
      show: false,
      // Marshrut kelganda xarita uni to'liq qamrab oladigan qilib moslashadi.
      fitSelectedRoutes: true,
      routeWhileDragging: false,
      // LRM standart holda har qanday xatoni `console.error('Routing error:', ...)`
      // bilan yozadi — jumladan biz O'ZIMIZ bekor qilgan so'rovlarni ham. Xatoni
      // quyida o'zimiz qayta ishlaymiz, shuning uchun bu ishlov bekor qilinadi.
      defaultErrorHandler: () => {},
    }).addTo(map);

    routingRef.current = routing;

    routing.on('routingerror', () => {
      // Kechikib kelgan xatoni e'tiborsiz qoldiramiz. Bu control allaqachon
      // almashtirilgan (props o'zgargan) yoki xarita yo'q qilingan bo'lsa, xato
      // endi dolzarb emas — aks holda foydalanuvchi ishlab turgan marshrut ustida
      // yolg'on "hisoblab bo'lmadi" xabarini ko'rardi.
      if (routingRef.current !== routing || !mapRef.current) return;

      setRoutingFailed(true);
      // Zaxira: to'g'ri punktir chiziq. Marshrut emas, lekin yo'nalish ko'rinadi.
      if (!mapRef.current) return;
      fallbackLineRef.current = L.polyline([originLatLng, destinationLatLng], {
        color: '#9CA3AF',
        weight: 3,
        dashArray: '6 8',
      }).addTo(mapRef.current);
      mapRef.current.fitBounds(L.latLngBounds([originLatLng, destinationLatLng]), {
        padding: FIT_PADDING,
      });
    });

    // Bu yerda `return () => ...` tozalash ATAYLAB yo'q: control effektning
    // boshida `map.removeControl` bilan, komponent yo'q qilinganda esa birinchi
    // effektdagi `map.remove()` bilan olib tashlanadi. Control olib tashlangach
    // uning hodisa tinglovchisi ham u bilan birga yo'qoladi.
  }, [origin, destination]);

  // ── 3. Haydovchining jonli nuqtasi ───────────────────────────────────────
  // ALOHIDA effektda: joylashuv bir necha soniyada yangilanadi va bu marshrutni
  // qayta hisoblashga sabab bo'lmasligi kerak (har yangilanishda OSRM'ga so'rov
  // ketardi va chiziq miltillardi).
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (!driverLocation) {
      driverMarkerRef.current?.remove();
      driverMarkerRef.current = null;
      return;
    }

    const latLng = toLatLng(driverLocation);
    if (driverMarkerRef.current) {
      driverMarkerRef.current.setLatLng(latLng);
    } else {
      driverMarkerRef.current = L.marker(latLng, {
        icon: circleIcon(styles.markerDriver),
        title: 'Haydovchi',
        // Marshrut chizig'i va A/B belgilaridan ustida turadi.
        zIndexOffset: 1000,
      }).addTo(map);
    }
  }, [driverLocation]);

  return (
    <div className={styles.container} ref={containerRef}>
      {routingFailed && (
        <div className={styles.error}>
          Marshrutni hisoblab bo'lmadi — taxminiy yo'nalish ko'rsatilgan
        </div>
      )}
    </div>
  );
}
