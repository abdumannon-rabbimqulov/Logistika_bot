import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getOrder, listMyOrders } from '../api/orders';
import { listTruckTypes } from '../api/truckTypes';
import { BottomNav } from '../components/BottomNav';
import { ChevronRightIcon, HomeAddressIcon, InfoIcon, PinIcon, PlusIcon, ProfileIcon, WorkAddressIcon, truckIconFor } from '../components/icons';
import { BellIcon } from '../components/icons';
import { useSavedAddresses } from '../hooks/useSavedAddresses';
import type { OrderDetail, OrderListItem, TruckType } from '../types/api';
import type { OrderPrefillState } from '../types/navigation';
import { formatPrice, formatRelativeDate, routeLabel, statusLabel } from '../utils/format';
import styles from './HomePage.module.css';

const ACTIVE_STATUSES = new Set(['SCHEDULED', 'ACCEPTED', 'IN_PROGRESS']);
const PAST_STATUSES = new Set(['COMPLETED', 'CANCELLED']);

export function HomePage() {
  const navigate = useNavigate();
  const { addresses } = useSavedAddresses();
  const [truckTypes, setTruckTypes] = useState<TruckType[]>([]);
  const [activeOrder, setActiveOrder] = useState<OrderDetail | null>(null);
  const [recentOrders, setRecentOrders] = useState<OrderDetail[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [types, orders] = await Promise.all([listTruckTypes(), listMyOrders()]);
        if (cancelled) return;
        setTruckTypes(types);

        const activeItem = orders.find((o: OrderListItem) => ACTIVE_STATUSES.has(o.status));
        const recentItems = orders.filter((o: OrderListItem) => PAST_STATUSES.has(o.status)).slice(0, 3);

        const [activeDetail, ...recentDetails] = await Promise.all([
          activeItem ? getOrder(activeItem.id) : Promise.resolve(null),
          ...recentItems.map((o: OrderListItem) => getOrder(o.id)),
        ]);
        if (cancelled) return;
        setActiveOrder(activeDetail);
        setRecentOrders(recentDetails);
      } catch {
        // Ro'yxatlar yuklanmasa ham asosiy CTA (yangi buyurtma) ishlashda davom etadi.
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  function goToOrderScreen(prefill?: OrderPrefillState) {
    navigate('/order/new', { state: prefill });
  }

  const activeTruckType = activeOrder
    ? truckTypes.find((t) => t.id === activeOrder.required_truck_type_id)
    : undefined;
  const ActiveTruckIcon = truckIconFor(activeTruckType?.name ?? '');

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <div className={styles.topBar}>
          <div className={styles.wordmark}>YUK</div>
          <div className={styles.topActions}>
            <button className={styles.iconCircle} onClick={() => navigate('/messages')} aria-label="Xabarlar">
              <BellIcon />
            </button>
            <button className={styles.iconCircle} onClick={() => navigate('/profile')} aria-label="Profil">
              <ProfileIcon />
            </button>
          </div>
        </div>

        <div className={styles.section}>
          <button className={styles.mainCta} onClick={() => goToOrderScreen()}>
            <div className={styles.mainCtaIcon}>
              <PinIcon />
            </div>
            <div className={styles.mainCtaText}>
              <div className={styles.mainCtaTitle}>Qayerga yuk jo'natasiz?</div>
              <div className={styles.mainCtaSubtitle}>Manzilni kiriting va bir necha soniyada narxni bilib oling</div>
            </div>
            <ChevronRightIcon />
          </button>
        </div>

        {activeOrder && (
          <div className={styles.section}>
            <button className={styles.activeCard} onClick={() => navigate(`/orders/${activeOrder.id}`)}>
              <div className={styles.activeTop}>
                <div className={styles.activeStatus}>
                  <span className={styles.activeDot} />
                  <span>{statusLabel(activeOrder.status)}</span>
                </div>
              </div>
              <div className={styles.activeBody}>
                <div className={styles.activeIconBox}>
                  <ActiveTruckIcon color="#fff" />
                </div>
                <div className={styles.activeInfo}>
                  <div className={styles.activeRoute}>
                    {routeLabel(activeOrder.origin?.address, activeOrder.destination?.address)}
                  </div>
                  <div className={styles.activeMeta}>{formatPrice(activeOrder.price)} {activeOrder.currency}</div>
                </div>
                <span className={styles.trackBtn}>Kuzatish</span>
              </div>
            </button>
          </div>
        )}

        {truckTypes.length > 0 && (
          <div style={{ paddingTop: 22 }}>
            <div className={styles.sectionTitle}>Transport turini tanlang</div>
            <div className={styles.transportScroll}>
              {truckTypes.map((t) => {
                const Icon = truckIconFor(t.name);
                return (
                  <button
                    key={t.id}
                    className={styles.transportItem}
                    onClick={() => goToOrderScreen({ truckTypeId: t.id })}
                  >
                    <div className={styles.transportIconBox}>
                      <Icon />
                    </div>
                    <span className={styles.transportLabel}>{t.name}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        <div className={styles.section}>
          <div className={styles.sectionTitle} style={{ padding: 0 }}>
            Saqlangan manzillar
          </div>
          <div style={{ marginTop: 8 }}>
            {addresses.length === 0 && <div className={styles.emptyHint}>Hali saqlangan manzil yo'q</div>}
            {addresses.map((a) => (
              <button
                key={a.id}
                className={styles.addressRow}
                onClick={() =>
                  goToOrderScreen({
                    destination: { address: a.address, latitude: a.latitude, longitude: a.longitude },
                  })
                }
              >
                <div className={styles.addressIconBox}>
                  {a.label.toLowerCase().includes('ish') ? <WorkAddressIcon /> : <HomeAddressIcon />}
                </div>
                <div className={styles.addressInfo}>
                  <div className={styles.addressLabel}>{a.label}</div>
                  <div className={styles.addressSub}>{a.address}</div>
                </div>
              </button>
            ))}
            <button className={styles.addressRow} onClick={() => navigate('/order/new', { state: { openSaveAddress: true } })}>
              <div className={styles.addressIconBox}>
                <PlusIcon color="var(--color-text-primary)" />
              </div>
              <div className={styles.addressInfo}>
                <div className={styles.addressLabel}>Manzil qo'shish</div>
              </div>
            </button>
          </div>
        </div>

        {recentOrders.length > 0 && (
          <div className={styles.section}>
            <div className={styles.sectionTitle} style={{ padding: 0 }}>
              Oxirgi buyurtmalar
            </div>
            <div className={styles.recentList}>
              {recentOrders.map((order) => {
                const truckType = truckTypes.find((t) => t.id === order.required_truck_type_id);
                return (
                  <div key={order.id} className={styles.recentCard}>
                    <div className={styles.recentInfo}>
                      <div className={styles.recentRoute}>
                        {routeLabel(order.origin?.address, order.destination?.address)}
                      </div>
                      <div className={styles.recentMeta}>
                        {formatRelativeDate(order.created_at)} · {truckType?.name ?? ''}
                      </div>
                    </div>
                    <button
                      className={styles.repeatBtn}
                      onClick={() =>
                        goToOrderScreen({
                          truckTypeId: order.required_truck_type_id,
                          origin: order.origin
                            ? { address: order.origin.address ?? '', latitude: Number(order.origin.latitude), longitude: Number(order.origin.longitude) }
                            : undefined,
                          destination: order.destination
                            ? {
                                address: order.destination.address ?? '',
                                latitude: Number(order.destination.latitude),
                                longitude: Number(order.destination.longitude),
                              }
                            : undefined,
                        })
                      }
                    >
                      Takrorlash
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div className={styles.section} style={{ paddingBottom: 24 }}>
          <div className={styles.banner}>
            <InfoIcon />
            <div className={styles.bannerText}>Yangi haydovchilar uchun tekshiruv kuchaytirildi — yukingiz xavfsiz qo'lda.</div>
          </div>
        </div>
      </div>

      <BottomNav />
    </div>
  );
}
