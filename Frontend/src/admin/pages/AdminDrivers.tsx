import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../../api/client';
import { driverLocationsWsUrl, listDriverMonitor } from '../../api/admin';
import type { DriverLocationItem, DriverMonitorItem } from '../../types/api';
import { DriverMonitorDrawer } from '../components/DriverMonitorDrawer';
import { DriversMap, markerColor, statusLabelOf } from '../components/DriversMap';
import { SearchIconAdmin } from '../icons';
import shared from '../shared.module.css';
import styles from './AdminDrivers.module.css';
import { DriverBlocksPanel } from './DriverBlocksPanel';

type WsStatus = 'connecting' | 'live' | 'offline';
type Tab = 'map' | 'accounts';

/** Xarita ma'lumotini qayta so'rash oralig'i — holat/yuk o'zgarishlari uchun.
 *  Koordinatalar bundan tashqari WS orqali darhol yangilanadi. */
const POLL_MS = 8000;

export function AdminDrivers() {
  const [tab, setTab] = useState<Tab>('map');
  const [drivers, setDrivers] = useState<DriverMonitorItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [search, setSearch] = useState('');
  const [wsStatus, setWsStatus] = useState<WsStatus>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    try {
      // Koordinatasi yo'q haydovchilar xaritada ko'rsatilmaydi (only_with_location=true).
      const items = await listDriverMonitor(true);
      setDrivers(items);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Haydovchilar yuklanmadi');
    } finally {
      setLoading(false);
    }
  }, []);

  // 1) Polling — status va yuk holati uchun (WS faqat koordinata beradi).
  useEffect(() => {
    if (tab !== 'map') return;
    void load();
    pollRef.current = window.setInterval(() => void load(), POLL_MS);
    return () => {
      if (pollRef.current != null) window.clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [tab, load]);

  // 2) WebSocket — markerlar pollingni kutmasdan siljiydi.
  useEffect(() => {
    if (tab !== 'map') return;
    let ws: WebSocket | null = null;
    let cancelled = false;

    const applyLive = (item: DriverLocationItem) => {
      setDrivers((prev) =>
        prev.map((d) =>
          d.driver_id === item.driver_id
            ? {
                ...d,
                latitude: item.lat,
                longitude: item.lon,
                location_source: 'live' as const,
                location_at: item.ts,
                online: true,
              }
            : d,
        ),
      );
    };

    try {
      ws = new WebSocket(driverLocationsWsUrl());
      ws.onopen = () => !cancelled && setWsStatus('live');
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.event === 'snapshot' && Array.isArray(msg.items)) {
            (msg.items as DriverLocationItem[]).forEach(applyLive);
          } else if (msg.event === 'update' && msg.item) {
            const item = msg.item as DriverLocationItem & { stopped?: boolean };
            if (item.stopped) {
              // Translyatsiya to'xtadi — haydovchi oflayn bo'ldi, keyingi polling
              // uni "oxirgi ma'lum joylashuv" bilan kulrang qilib ko'rsatadi.
              setDrivers((prev) =>
                prev.map((d) => (d.driver_id === item.driver_id ? { ...d, online: false } : d)),
              );
            } else {
              applyLive(item);
            }
          }
        } catch {
          // yaroqsiz xabar — e'tiborsiz
        }
      };
      ws.onerror = () => !cancelled && setWsStatus('offline');
      ws.onclose = () => !cancelled && setWsStatus('offline');
    } catch {
      setWsStatus('offline');
    }

    return () => {
      cancelled = true;
      ws?.close();
    };
  }, [tab]);

  const filtered = search.trim()
    ? drivers.filter((d) => {
        const q = search.trim().toLowerCase();
        return (
          (d.full_name ?? '').toLowerCase().includes(q) ||
          d.truck_number.toLowerCase().includes(q) ||
          (d.phone_number ?? '').includes(q)
        );
      })
    : drivers;

  const selected = drivers.find((d) => d.driver_id === selectedId) ?? null;
  const onlineCount = drivers.filter((d) => d.online).length;
  const busyCount = drivers.filter((d) => d.busy).length;

  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <h1 className={shared.pageTitle}>Haydovchilar</h1>
          <div className={shared.pageSub}>
            {tab === 'map'
              ? `Xaritada ${drivers.length} ta · onlayn ${onlineCount} · yuk bilan ${busyCount}`
              : 'Balans, qarz uchun avtomatik blok va blokdan chiqarish'}
          </div>
        </div>
        {tab === 'map' && (
          <div className={styles.wsBadge} data-status={wsStatus}>
            <span className={styles.wsDot} />
            {wsStatus === 'live'
              ? 'Real-time ulangan'
              : wsStatus === 'connecting'
                ? 'Ulanmoqda...'
                : `Polling (${POLL_MS / 1000}s)`}
          </div>
        )}
      </div>

      <div className={styles.tabs}>
        <button className={tab === 'map' ? styles.tabActive : styles.tab} onClick={() => setTab('map')}>
          Xarita
        </button>
        <button
          className={tab === 'accounts' ? styles.tabActive : styles.tab}
          onClick={() => setTab('accounts')}
        >
          Balans va bloklar
        </button>
      </div>

      {tab === 'accounts' ? (
        <DriverBlocksPanel />
      ) : (
        <>
          {error && <div className={shared.errorBanner}>{error}</div>}

          <div className={styles.monitor}>
            {/* Chap ustun: qidiruv + haydovchilar ro'yxati (xarita bilan sinxron) */}
            <div className={styles.sidePanel}>
              <div className={styles.searchBox}>
                <SearchIconAdmin />
                <input
                  className={styles.searchInput}
                  placeholder="Ism, raqam yoki telefon"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>

              <div className={styles.list}>
                {loading && <div className={styles.muted}>Yuklanmoqda...</div>}
                {!loading && filtered.length === 0 && (
                  <div className={styles.muted}>Joylashuvi ma’lum haydovchi yo‘q</div>
                )}
                {filtered.map((d) => (
                  <button
                    key={d.driver_id}
                    className={d.driver_id === selectedId ? styles.listItemActive : styles.listItem}
                    onClick={() => setSelectedId(d.driver_id)}
                  >
                    <span className={styles.listDot} style={{ background: markerColor(d) }} />
                    <span className={styles.listInfo}>
                      <span className={styles.listName}>
                        {d.full_name ?? `Haydovchi #${d.driver_id}`}
                      </span>
                      <span className={styles.listMeta}>
                        {d.truck_number} · {statusLabelOf(d)}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Asosiy qism: xarita */}
            <div className={styles.mapArea}>
              <DriversMap drivers={filtered} selectedId={selectedId} onSelect={setSelectedId} />
            </div>

            {/* O'ng panel: tanlangan haydovchi tafsilotlari */}
            {selected && (
              <DriverMonitorDrawer driver={selected} onClose={() => setSelectedId(null)} />
            )}
          </div>
        </>
      )}
    </div>
  );
}
