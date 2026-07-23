import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { createOrder, estimatePrice, reverseGeocode } from '../api/orders';
import { AddressSearchSheet } from '../components/AddressSearchSheet';
import { type CargoDetails, CargoDetailsSheet } from '../components/CargoDetailsSheet';
import { YandexMap, type YandexMapHandle } from '../components/YandexMap';
import {
  BackIcon,
  CardIcon,
  ClockIcon,
  DestinationFlagIcon,
  LocationIcon,
  PlusIcon,
  ProfileIcon,
  SearchIcon,
  SettingsIcon,
  SwapIcon,
  truckIconFor,
} from '../components/icons';
import { ApiError } from '../api/client';
import { useGeolocation } from '../hooks/useGeolocation';
import type { GeocodeSuggestion, OrderCreateInput, PriceEstimateOption } from '../types/api';
import type { OrderPointPrefill, OrderPrefillState } from '../types/navigation';
import { formatEta, formatPrice } from '../utils/format';
import styles from './OrderPage.module.css';

type AddressSheetTarget = 'origin' | 'destination' | null;

export function OrderPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const prefill = (location.state as OrderPrefillState | null) ?? null;
  const geolocation = useGeolocation();
  const mapRef = useRef<YandexMapHandle>(null);

  const [origin, setOrigin] = useState<OrderPointPrefill | null>(prefill?.origin ?? null);
  const [destination, setDestination] = useState<OrderPointPrefill | null>(prefill?.destination ?? null);
  const [selectedTruckTypeId, setSelectedTruckTypeId] = useState<number | null>(prefill?.truckTypeId ?? null);
  const [options, setOptions] = useState<PriceEstimateOption[]>([]);
  const [distanceKm, setDistanceKm] = useState<number | null>(null);
  const [durationMin, setDurationMin] = useState<number | null>(null);
  const [routeGeometry, setRouteGeometry] = useState<[number, number][] | null>(null);
  const [estimating, setEstimating] = useState(false);
  const [addressSheet, setAddressSheet] = useState<AddressSheetTarget>(null);
  const [cargoSheetOpen, setCargoSheetOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Joriy manzilni avtomatik aniqlash (faqat origin hali berilmagan bo'lsa)
  useEffect(() => {
    if (origin || !geolocation.coords) return;
    const { latitude, longitude } = geolocation.coords;
    reverseGeocode(latitude, longitude)
      .then((res) => {
        setOrigin({ address: res.address ?? "Joriy joylashuv", latitude, longitude });
      })
      .catch(() => {
        // aniqlanmasa — foydalanuvchi "Qidirish" orqali qo'lda tanlaydi
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [geolocation.coords]);

  // Ikkala manzil ham bo'lganda narx/masofa hisoblanadi
  useEffect(() => {
    if (!origin || !destination) {
      setOptions([]);
      setDistanceKm(null);
      setDurationMin(null);
      setRouteGeometry(null);
      return;
    }
    let cancelled = false;
    setEstimating(true);
    estimatePrice(
      { latitude: origin.latitude, longitude: origin.longitude },
      { latitude: destination.latitude, longitude: destination.longitude },
    )
      .then((res) => {
        if (cancelled) return;
        setOptions(res.options);
        setDistanceKm(res.distance_km);
        setDurationMin(res.duration_min);
        setRouteGeometry(res.route_geometry?.length ? res.route_geometry : null);
        setSelectedTruckTypeId((prev) => prev ?? res.options[0]?.truck_type_id ?? null);
      })
      .catch(() => {
        if (cancelled) return;
        setOptions([]);
        setRouteGeometry(null);
      })
      .finally(() => {
        if (!cancelled) setEstimating(false);
      });
    return () => {
      cancelled = true;
    };
  }, [origin, destination]);

  function handleSwap() {
    setOrigin(destination);
    setDestination(origin);
  }

  // "Mening joylashuvim" tugmasi — xaritani foydalanuvchi joylashuviga yaqinlashtiradi.
  // Avval useGeolocation aniqlagan koordinata ishlatiladi; hali aniqlanmagan bo'lsa
  // (yoki ruxsat endi berilgan bo'lsa) qaytadan so'raladi.
  function handleMyLocation() {
    const focus = (lat: number, lon: number) => mapRef.current?.focusLocation(lat, lon);
    if (geolocation.coords) {
      focus(geolocation.coords.latitude, geolocation.coords.longitude);
    } else if (origin) {
      focus(origin.latitude, origin.longitude);
    } else if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => focus(pos.coords.latitude, pos.coords.longitude),
        undefined,
        { enableHighAccuracy: true, timeout: 8000 },
      );
    }
  }

  function handleAddressSelected(suggestion: GeocodeSuggestion) {
    const point: OrderPointPrefill = { address: suggestion.address, latitude: suggestion.latitude, longitude: suggestion.longitude };
    if (addressSheet === 'origin') setOrigin(point);
    if (addressSheet === 'destination') setDestination(point);
    setAddressSheet(null);
  }

  const selectedOption = useMemo(
    () => options.find((o) => o.truck_type_id === selectedTruckTypeId) ?? null,
    [options, selectedTruckTypeId],
  );

  const canSubmit = Boolean(origin && destination && selectedTruckTypeId && !estimating);

  async function handleCargoSubmit(details: CargoDetails) {
    if (!origin || !destination || !selectedTruckTypeId) return;
    setSubmitting(true);
    setSubmitError(null);
    const payload: OrderCreateInput = {
      cargo_name: details.cargoName,
      weight: details.weight,
      volume: details.volume,
      pickup_at: new Date().toISOString(),
      required_truck_type_id: selectedTruckTypeId,
      waypoints: [
        { sequence: 1, type: 'PICKUP', address: origin.address, latitude: origin.latitude, longitude: origin.longitude },
        { sequence: 2, type: 'DELIVERY', address: destination.address, latitude: destination.latitude, longitude: destination.longitude },
      ],
    };
    try {
      const order = await createOrder(payload);
      navigate(`/orders/${order.id}`, { replace: true });
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Buyurtma yaratilmadi, qayta urinib ko'ring");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.mapLayer}>
        <YandexMap ref={mapRef} origin={origin} destination={destination} route={routeGeometry} />
        {durationMin !== null && (
          <div className={styles.etaBadge}>
            <ClockIcon />
            {formatEta(durationMin)} da yetib keladi
          </div>
        )}
        <button className={styles.myLocationBtn} onClick={handleMyLocation} aria-label="Mening joylashuvim">
          <LocationIcon />
        </button>
      </div>

      <div className={styles.topBar}>
        <button className={styles.iconBtn} onClick={() => navigate('/profile')} aria-label="Profil">
          <ProfileIcon color="var(--color-gray-800)" strokeWidth={1.9} />
        </button>
      </div>
      <div className={styles.topBarSecondary}>
        <button className={styles.iconBtn} onClick={() => navigate(-1)} aria-label="Orqaga">
          <BackIcon />
        </button>
        <button className={styles.iconBtn} onClick={handleSwap} aria-label="Manzillarni almashtirish">
          <SwapIcon />
        </button>
      </div>

      <div className={styles.sheet}>
        <div className={styles.dragHandle} />

        <div className={styles.addressBlock}>
          <button className={styles.addressRow} onClick={() => setAddressSheet('origin')}>
            <span className={styles.originDot} />
            <div className={styles.rowText}>
              <div className={styles.rowLabel}>{origin ? "Qayerdan" : "Joriy manzil aniqlanmoqda..."}</div>
              {origin ? (
                <div className={styles.rowValue}>{origin.address}</div>
              ) : (
                <div className={styles.rowValuePlaceholder}>Manzil tanlang</div>
              )}
            </div>
            <span className={styles.searchPill}>
              <SearchIcon />
              Qidirish
            </span>
          </button>

          <button className={styles.addressRow} onClick={() => setAddressSheet('destination')}>
            <DestinationFlagIcon />
            <div className={styles.rowText}>
              <div className={styles.rowLabel}>Qayerga</div>
              {destination ? (
                <div className={styles.rowValue}>
                  {destination.address}
                  {distanceKm !== null ? ` · ${Math.round(distanceKm)} km` : ''}
                </div>
              ) : (
                <div className={styles.rowValuePlaceholder}>Manzil tanlang</div>
              )}
            </div>
            <span className={styles.addBtn}>
              <PlusIcon />
            </span>
          </button>
        </div>

        {options.length > 0 && (
          <>
            <div className={styles.tabsRow}>
              <span className={styles.tab}>Hammasi</span>
              {options.map((opt) => (
                <span
                  key={opt.truck_type_id}
                  className={opt.truck_type_id === selectedTruckTypeId ? styles.tabActive : styles.tab}
                  onClick={() => setSelectedTruckTypeId(opt.truck_type_id)}
                >
                  {opt.name}
                </span>
              ))}
            </div>

            <div className={styles.truckRow}>
              {options.map((opt) => {
                const Icon = truckIconFor(opt.name);
                const selected = opt.truck_type_id === selectedTruckTypeId;
                return (
                  <button
                    key={opt.truck_type_id}
                    className={selected ? styles.truckCardSelected : styles.truckCard}
                    onClick={() => setSelectedTruckTypeId(opt.truck_type_id)}
                  >
                    <Icon color={selected ? 'var(--color-accent-pressed)' : 'var(--color-text-secondary)'} />
                    {durationMin !== null && (
                      <span className={selected ? styles.truckDurationSelected : styles.truckDuration}>
                        {Math.round(durationMin)} daq
                      </span>
                    )}
                    <span className={selected ? styles.truckNameSelected : styles.truckName}>{opt.name}</span>
                    <span className={selected ? styles.truckPriceSelected : styles.truckPrice}>{formatPrice(opt.price)}</span>
                  </button>
                );
              })}
            </div>
          </>
        )}

        {estimating && <div className={styles.tab} style={{ padding: '0 18px' }}>Narx hisoblanmoqda...</div>}
        {submitError && <div className={styles.errorBanner}>{submitError}</div>}

        <div className={styles.ctaRow}>
          <span className={styles.ctaSideBtn}>
            <CardIcon />
          </span>
          <button className={styles.ctaMain} disabled={!canSubmit} onClick={() => setCargoSheetOpen(true)}>
            {selectedOption ? `Buyurtma berish · ${formatPrice(selectedOption.price)}` : 'Buyurtma berish'}
          </button>
          <span className={styles.ctaSideBtn}>
            <SettingsIcon />
          </span>
        </div>
      </div>

      {addressSheet && (
        <AddressSearchSheet
          title={addressSheet === 'origin' ? "Qayerdan olib ketamiz?" : "Qayerga olib boramiz?"}
          onSelect={handleAddressSelected}
          onClose={() => setAddressSheet(null)}
        />
      )}

      {cargoSheetOpen && (
        <CargoDetailsSheet
          onSubmit={handleCargoSubmit}
          onClose={() => setCargoSheetOpen(false)}
          submitting={submitting}
          apiError={submitError}
        />
      )}
    </div>
  );
}
