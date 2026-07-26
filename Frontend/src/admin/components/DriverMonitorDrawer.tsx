import type { DriverMonitorItem } from '../../types/api';
import { formatPrice, statusLabel } from '../../utils/format';
import { markerColor, statusLabelOf } from './DriversMap';
import styles from './DriverMonitorDrawer.module.css';

interface Props {
  driver: DriverMonitorItem;
  onClose: () => void;
}

function formatWhen(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  const diffSec = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
  if (diffSec < 60) return `${diffSec} soniya oldin`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)} daqiqa oldin`;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Xaritadagi markerga bosilganda o'ngdan ochiladigan panel — haydovchi va yuk tafsilotlari. */
export function DriverMonitorDrawer({ driver, onClose }: Props) {
  const order = driver.active_order;
  const progress =
    order && order.total_waypoints > 0
      ? Math.round((order.completed_waypoints / order.total_waypoints) * 100)
      : 0;

  return (
    <aside className={styles.drawer} role="dialog" aria-label="Haydovchi ma'lumotlari">
      <div className={styles.head}>
        <div>
          <div className={styles.name}>{driver.full_name ?? `Haydovchi #${driver.driver_id}`}</div>
          <div className={styles.sub}>ID #{driver.driver_id}</div>
        </div>
        <button className={styles.close} onClick={onClose} aria-label="Yopish">
          ×
        </button>
      </div>

      <div className={styles.statusRow}>
        <span className={styles.statusChip} style={{ background: markerColor(driver) }}>
          {statusLabelOf(driver)}
        </span>
        <span className={styles.locSource}>
          {driver.location_source === 'live'
            ? 'Jonli GPS'
            : driver.location_source === 'last_known'
              ? 'Oxirgi ma’lum joylashuv'
              : 'Joylashuv yo‘q'}{' '}
          · {formatWhen(driver.location_at)}
        </span>
      </div>

      <dl className={styles.rows}>
        <div className={styles.row}>
          <dt>Telefon</dt>
          <dd>
            {driver.phone_number ? (
              <a className={styles.link} href={`tel:${driver.phone_number}`}>
                {driver.phone_number}
              </a>
            ) : (
              '—'
            )}
          </dd>
        </div>
        <div className={styles.row}>
          <dt>Avtomobil</dt>
          <dd>{driver.truck_type_name ?? '—'}</dd>
        </div>
        <div className={styles.row}>
          <dt>Davlat raqami</dt>
          <dd>{driver.truck_number}</dd>
        </div>
        <div className={styles.row}>
          <dt>Reyting</dt>
          <dd>
            {Number(driver.rating).toFixed(1)} · {driver.total_trips} safar
          </dd>
        </div>
        <div className={styles.row}>
          <dt>Liniya holati</dt>
          <dd>{driver.is_available ? 'Liniyada' : 'Liniyadan chiqqan'}</dd>
        </div>
        {driver.latitude != null && driver.longitude != null && (
          <div className={styles.row}>
            <dt>Koordinata</dt>
            <dd>
              <a
                className={styles.link}
                href={`https://yandex.uz/maps/?pt=${driver.longitude},${driver.latitude}&z=15&l=map`}
                target="_blank"
                rel="noreferrer"
              >
                {driver.latitude.toFixed(5)}, {driver.longitude.toFixed(5)}
              </a>
            </dd>
          </div>
        )}
      </dl>

      <div className={styles.sectionTitle}>Yuk holati</div>

      {!order ? (
        <div className={styles.freeBox}>
          <span className={styles.freeDot} />
          Hozirda bo‘sh — yuk yo‘q
        </div>
      ) : (
        <div className={styles.cargoCard}>
          <div className={styles.cargoHead}>
            <span className={styles.orderId}>Buyurtma #{order.id}</span>
            <span className={styles.orderStatus}>{statusLabel(order.status)}</span>
          </div>

          <div className={styles.cargoName}>{order.cargo_name}</div>
          <div className={styles.cargoMeta}>
            {Number(order.weight)} t
            {order.volume != null ? ` · ${Number(order.volume)} m³` : ''} ·{' '}
            {formatPrice(Number(order.price))} {order.currency}
          </div>

          <div className={styles.route}>
            <div className={styles.routeRow}>
              <span className={styles.routeDotFrom} />
              <span className={styles.routeText}>{order.origin_address ?? '—'}</span>
            </div>
            <div className={styles.routeLine} />
            <div className={styles.routeRow}>
              <span className={styles.routeDotTo} />
              <span className={styles.routeText}>{order.destination_address ?? '—'}</span>
            </div>
          </div>

          {order.current_waypoint_address && (
            <div className={styles.currentPoint}>
              Keyingi nuqta: <strong>{order.current_waypoint_address}</strong>
            </div>
          )}

          <div className={styles.progressHead}>
            <span>Bajarilgan nuqtalar</span>
            <span>
              {order.completed_waypoints} / {order.total_waypoints}
            </span>
          </div>
          <div className={styles.progressTrack}>
            <div className={styles.progressFill} style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {driver.is_blocked && (
        <div className={styles.blocked}>
          Bloklangan: {driver.block_reason || "sabab ko'rsatilmagan"}
        </div>
      )}
    </aside>
  );
}
