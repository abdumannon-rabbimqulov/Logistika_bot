import { useEffect, useRef, useState } from 'react';
import {
  loadYandexMaps,
  UZBEKISTAN_CENTER,
  UZBEKISTAN_DEFAULT_ZOOM,
  type YMap,
} from '../../utils/yandexMaps';
import type { DriverMonitorItem } from '../../types/api';
import styles from './DriversMap.module.css';

interface Props {
  drivers: DriverMonitorItem[];
  selectedId: number | null;
  onSelect: (driverId: number) => void;
}

/** Marker rangi haydovchi holatiga qarab (legenda bilan bir xil). */
export function markerColor(d: DriverMonitorItem): string {
  if (!d.online) return '#8A93A2'; // oflayn — kulrang
  if (d.busy) return '#1D4ED8'; // yuk bilan — ko'k
  return '#16A34A'; // bo'sh — yashil
}

export function statusLabelOf(d: DriverMonitorItem): string {
  if (!d.online) return 'Oflayn';
  return d.busy ? 'Yuk bilan' : "Bo'sh";
}

const SELECTED_ZOOM = 13;

export function DriversMap({ drivers, selectedId, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<YMap | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  // Xarita birinchi ma'lumot kelganda bir marta markerlarga moslanadi; keyin admin
  // qo'lda surganini har 8 soniyalik yangilanish buzib yubormasligi kerak.
  const fittedRef = useRef(false);
  // Marker bosilganda React state'ga xabar berish uchun — ymaps callback'i eski
  // closure'ni ushlab qolmasligi uchun ref orqali.
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    let cancelled = false;
    let resizeObserver: ResizeObserver | null = null;

    loadYandexMaps()
      .then((ymaps) => {
        if (cancelled || !containerRef.current) return;
        const map = new ymaps.Map(
          containerRef.current,
          { center: UZBEKISTAN_CENTER, zoom: UZBEKISTAN_DEFAULT_ZOOM, controls: ['zoomControl'] },
          { minZoom: 4 },
        );
        // Yandex'ning o'z POI (do'kon, kafe...) balonlari o'chiriladi — monitoring
        // xaritasida marker o'rniga tasodifan POI ochilib ketmasligi uchun.
        map.options.set('yandexMapDisablePoiInteractivity', true);
        mapRef.current = map;
        setReady(true);
        resizeObserver = new ResizeObserver(() => map.container.fitToViewport());
        resizeObserver.observe(containerRef.current);
      })
      .catch(() => !cancelled && setFailed(true));

    return () => {
      cancelled = true;
      resizeObserver?.disconnect();
      mapRef.current?.destroy();
      mapRef.current = null;
    };
  }, []);

  // Markerlarni qayta chizish (har yangilanishda ro'yxat kichik — 100lab haydovchigacha
  // to'liq qayta chizish yetarlicha tez va holat mos kelishini kafolatlaydi).
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;

    let cancelled = false;
    loadYandexMaps().then((ymaps) => {
      if (cancelled) return;
      map.geoObjects.removeAll();

      const points: [number, number][] = [];
      for (const d of drivers) {
        if (d.latitude == null || d.longitude == null) continue;
        const point: [number, number] = [d.latitude, d.longitude];
        points.push(point);

        const placemark = new ymaps.Placemark(
          point,
          {
            hintContent: `${d.full_name ?? `Haydovchi #${d.driver_id}`} · ${d.truck_number}`,
            iconContent: d.busy ? '📦' : '',
          },
          {
            preset: d.busy ? 'islands#circleIconWithCaption' : 'islands#circleIcon',
            iconColor: markerColor(d),
            zIndex: d.driver_id === selectedId ? 1000 : 100,
            iconCaptionMaxWidth: '0',
          },
        ) as { events: { add(type: string, cb: () => void): void } };

        placemark.events.add('click', () => onSelectRef.current(d.driver_id));
        map.geoObjects.add(placemark);
      }

      if (!fittedRef.current && points.length > 0) {
        fittedRef.current = true;
        if (points.length === 1) {
          map.setCenter(points[0], SELECTED_ZOOM);
        } else {
          map.setBounds(ymaps.util.bounds.fromPoints(points), {
            checkZoomRange: true,
            zoomMargin: 60,
          });
        }
      }
    });

    return () => {
      cancelled = true;
    };
  }, [ready, drivers, selectedId]);

  // Ro'yxatdan haydovchi tanlanganda xarita o'sha nuqtaga uchadi.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || selectedId == null) return;
    const target = drivers.find((d) => d.driver_id === selectedId);
    if (target?.latitude != null && target.longitude != null) {
      map.setCenter([target.latitude, target.longitude], SELECTED_ZOOM, { duration: 300 });
    }
    // `drivers` ataylab bog'liqlikda emas: har pollingda qayta markazlashtirish
    // adminni xaritada "sakratib" yuborardi.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, selectedId]);

  return (
    <div className={styles.wrap}>
      <div ref={containerRef} className={styles.map} />
      {!ready && !failed && <div className={styles.spinner} aria-label="Xarita yuklanmoqda" />}
      {failed && <div className={styles.error}>Xarita yuklanmadi</div>}

      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <i className={styles.dotFree} /> Bo‘sh
        </span>
        <span className={styles.legendItem}>
          <i className={styles.dotBusy} /> Yuk bilan
        </span>
        <span className={styles.legendItem}>
          <i className={styles.dotOffline} /> Oflayn
        </span>
      </div>
    </div>
  );
}
