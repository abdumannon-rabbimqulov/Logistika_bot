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
}

export function YandexMap({ origin, destination }: Props) {
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

      if (points.length === 2) {
        map.setBounds(ymaps.util.bounds.fromPoints(points), { checkZoomRange: true, zoomMargin: 60 });
      } else if (points.length === 1) {
        map.setCenter(points[0], 13);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [ready, origin, destination]);

  return (
    <div className={styles.wrap}>
      <div ref={containerRef} className={styles.map} />
      {failed && <div className={styles.error}>Xarita yuklanmadi</div>}
    </div>
  );
}
