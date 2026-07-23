import { useEffect, useRef, useState } from 'react';
import {
  loadYandexMaps,
  UZBEKISTAN_BOUNDS,
  UZBEKISTAN_CENTER,
  UZBEKISTAN_DEFAULT_ZOOM,
  type YMap,
} from '../utils/yandexMaps';
import styles from './YandexMap.module.css';

interface MapPoint {
  latitude: number;
  longitude: number;
}

interface Props {
  origin?: MapPoint | null;
  destination?: MapPoint | null;
  /** OSRM marshrut chizig'i: [[latitude, longitude], ...] (backend `route_geometry`). */
  route?: [number, number][] | null;
}

export function YandexMap({ origin, destination, route }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<YMap | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;
    loadYandexMaps()
      .then((ymaps) => {
        if (cancelled || !containerRef.current) return;
        const map = new ymaps.Map(
          containerRef.current,
          { center: UZBEKISTAN_CENTER, zoom: UZBEKISTAN_DEFAULT_ZOOM, controls: ['zoomControl'] },
          { restrictMapArea: UZBEKISTAN_BOUNDS, minZoom: 5 },
        );
        mapRef.current = map;
        setReady(true);

        // Konteyner ymaps o'lchagan paytdan keyin o'zgarsa (masalan, layout hali
        // to'liq joylashmagan bo'lsa yoki klaviatura/varaqlar ekran balandligini
        // o'zgartirsa), plitkalar eski o'lchamda "qotib" qoladi — fitToViewport shuni tuzatadi.
        resizeObserver = new ResizeObserver(() => map.container.fitToViewport());
        resizeObserver.observe(containerRef.current);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      mapRef.current?.destroy();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;

    let cancelled = false;
    loadYandexMaps().then((ymaps) => {
      if (cancelled) return;
      map.geoObjects.removeAll();

      // Marshrut chizig'i belgilardan oldin qo'shiladi — shunda belgilar chiziq ustida qoladi.
      if (route && route.length >= 2) {
        map.geoObjects.add(
          new ymaps.Polyline(route, {}, { strokeColor: '#15803D', strokeWidth: 5, strokeOpacity: 0.8 }),
        );
      }

      const points: [number, number][] = [];
      if (origin) {
        points.push([origin.latitude, origin.longitude]);
        map.geoObjects.add(
          new ymaps.Placemark([origin.latitude, origin.longitude], {}, { preset: 'islands#circleIcon', iconColor: '#15803D' }),
        );
      }
      if (destination) {
        points.push([destination.latitude, destination.longitude]);
        map.geoObjects.add(
          new ymaps.Placemark([destination.latitude, destination.longitude], {}, { preset: 'islands#dotIcon', iconColor: '#0F1319' }),
        );
      }

      // Marshrut bo'lsa — butun chiziq ko'rinadigan qilib moslanadi (chiziq to'g'ri
      // yo'nalishda emas, egri bo'lgani uchun faqat ikki nuqta bo'yicha moslash yetarli emas).
      const fitPoints = route && route.length >= 2 ? route : points;
      if (fitPoints.length >= 2) {
        map.setBounds(ymaps.util.bounds.fromPoints(fitPoints), { checkZoomRange: true, zoomMargin: 60 });
      } else if (fitPoints.length === 1) {
        map.setCenter(fitPoints[0], 13);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [ready, origin, destination, route]);

  return (
    <div className={styles.wrap}>
      <div ref={containerRef} className={styles.map} />
      {failed && <div className={styles.error}>Xarita yuklanmadi</div>}
    </div>
  );
}
