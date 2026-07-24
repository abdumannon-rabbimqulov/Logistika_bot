import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../../api/client';
import { driverLocationsWsUrl, listDriverLocations } from '../../api/admin';
import type { DriverLocationItem } from '../../types/api';
import { DataTable, type Column } from '../components/DataTable';
import shared from '../shared.module.css';
import styles from './AdminDrivers.module.css';

type WsStatus = 'connecting' | 'live' | 'offline';

function timeAgo(ts: string): string {
  const diff = Math.max(0, Date.now() - new Date(ts).getTime());
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s oldin`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min} daq oldin`;
  return `${Math.floor(min / 60)} soat oldin`;
}

export function AdminDrivers() {
  const [drivers, setDrivers] = useState<Map<number, DriverLocationItem>>(new Map());
  const [wsStatus, setWsStatus] = useState<WsStatus>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef<number | null>(null);

  function upsert(items: DriverLocationItem[]) {
    setDrivers((prev) => {
      const next = new Map(prev);
      for (const it of items) next.set(it.driver_id, it);
      return next;
    });
  }

  useEffect(() => {
    let cancelled = false;
    let ws: WebSocket | null = null;

    const startPolling = () => {
      if (pollRef.current != null) return;
      const poll = () =>
        listDriverLocations()
          .then((items) => {
            if (cancelled) return;
            setDrivers(new Map(items.map((it) => [it.driver_id, it])));
          })
          .catch(() => {});
      void poll();
      pollRef.current = window.setInterval(poll, 10_000);
    };

    // Boshlang'ich ro'yxat (WS ulanmaguncha darrov ko'rsatish uchun)
    listDriverLocations()
      .then((items) => {
        if (cancelled) return;
        setDrivers(new Map(items.map((it) => [it.driver_id, it])));
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'Lokatsiyalar yuklanmadi');
      })
      .finally(() => !cancelled && setLoading(false));

    // Real-time oqim
    try {
      ws = new WebSocket(driverLocationsWsUrl());
      ws.onopen = () => !cancelled && setWsStatus('live');
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.event === 'snapshot' && Array.isArray(msg.items)) {
            setDrivers(new Map((msg.items as DriverLocationItem[]).map((it) => [it.driver_id, it])));
          } else if (msg.event === 'update' && msg.item) {
            upsert([msg.item as DriverLocationItem]);
          }
        } catch {
          // yaroqsiz xabar — e'tiborsiz qoldiramiz
        }
      };
      ws.onerror = () => {
        if (!cancelled) {
          setWsStatus('offline');
          startPolling();
        }
      };
      ws.onclose = () => {
        if (!cancelled) {
          setWsStatus('offline');
          startPolling();
        }
      };
    } catch {
      setWsStatus('offline');
      startPolling();
    }

    return () => {
      cancelled = true;
      ws?.close();
      if (pollRef.current != null) window.clearInterval(pollRef.current);
    };
  }, []);

  const rows = Array.from(drivers.values()).sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime());

  const columns: Column<DriverLocationItem>[] = [
    {
      key: 'driver',
      header: 'Haydovchi',
      render: (d) => (
        <div className={styles.driverCell}>
          <span className={styles.onlineDot} />
          <div>
            <div className={styles.name}>{d.full_name ?? `Haydovchi #${d.driver_id}`}</div>
            <div className={styles.sub}>ID #{d.driver_id}</div>
          </div>
        </div>
      ),
    },
    { key: 'truck_number', header: 'Davlat raqami', render: (d) => d.truck_number ?? '—' },
    {
      key: 'coords',
      header: 'Koordinata',
      render: (d) => (
        <span className={shared.mono}>
          {d.lat.toFixed(5)}, {d.lon.toFixed(5)}
        </span>
      ),
    },
    { key: 'ts', header: 'Yangilangan', render: (d) => timeAgo(d.ts) },
    {
      key: 'map',
      header: '',
      align: 'right',
      render: (d) => (
        <a
          className={styles.mapLink}
          href={`https://yandex.uz/maps/?pt=${d.lon},${d.lat}&z=15&l=map`}
          target="_blank"
          rel="noreferrer"
        >
          Xaritada
        </a>
      ),
    },
  ];

  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <h1 className={shared.pageTitle}>Haydovchilar</h1>
          <div className={shared.pageSub}>Jonli GPS bo'yicha liniyadagi haydovchilar</div>
        </div>
        <div className={styles.wsBadge} data-status={wsStatus}>
          <span className={styles.wsDot} />
          {wsStatus === 'live' ? 'Real-time ulangan' : wsStatus === 'connecting' ? 'Ulanmoqda...' : 'Polling (10s)'}
        </div>
      </div>

      {error && <div className={shared.errorBanner}>{error}</div>}

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(d) => d.driver_id}
        loading={loading}
        emptyText="Hozircha liniyada jonli haydovchi yo'q"
      />
    </div>
  );
}
