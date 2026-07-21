import { useState } from 'react';
import { ApiError } from '../api/client';
import { updateDriverAvailability } from '../api/drivers';
import { GoOnlineSheet, type GoOnlineResult } from '../components/GoOnlineSheet';
import type { DriverCabinet } from '../types/api';
import { formatPrice } from '../utils/format';
import styles from './DriverHomePage.module.css';

interface Props {
  cabinet: DriverCabinet;
  onUpdated: (cabinet: DriverCabinet) => void;
}

function formatAvailableFrom(dateIso: string): string {
  return new Date(dateIso).toLocaleDateString('uz-UZ', { day: 'numeric', month: 'long' });
}

// To'liq haydovchi kabineti (buyurtmalar tarixi, safar e'lonlari, GPS xaritasi va h.k.)
// hali qurilmagan — bu shu qadar: profil xulosasi + liniyaga chiqish tugmasi. Yangi
// buyurtma takliflari hozircha Telegram bot orqali keladi (handlers/dispatch.py,
// services/dispatch.py) — Mini Appda qabul qilish keyingi bosqichda qo'shiladi.
export function DriverHomePage({ cabinet, onUpdated }: Props) {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleGoOnline(result: GoOnlineResult) {
    setSubmitting(true);
    setError(null);
    try {
      const updated = await updateDriverAvailability({
        is_available: true,
        current_city: result.currentCity,
        current_region: result.currentRegion,
        available_from_date: result.availableFromDate,
      });
      onUpdated(updated);
      setSheetOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "O'zgartirib bo'lmadi");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoOffline() {
    setSubmitting(true);
    setError(null);
    try {
      // available_from_date ham tozalanadi — keyingi safar liniyaga kirishda qayta so'raladi.
      const updated = await updateDriverAvailability({ is_available: false, available_from_date: null });
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "O'zgartirib bo'lmadi");
    } finally {
      setSubmitting(false);
    }
  }

  const isFutureAvailability = Boolean(cabinet.available_from_date) && new Date(cabinet.available_from_date!) > new Date();

  return (
    <div className={styles.page}>
      <div className={styles.title}>Haydovchi kabineti</div>

      <div className={styles.card}>
        <div className={styles.name}>{cabinet.name}</div>
        <div className={styles.truck}>
          {cabinet.truck_type_name ?? ''} · {cabinet.truck_number}
          {cabinet.truck_year ? ` · ${cabinet.truck_year}` : ''}
        </div>
        <div className={styles.balanceRow}>
          <span className={styles.balanceLabel}>Balans</span>
          <span className={styles.balanceValue}>{formatPrice(cabinet.balance_amount)} {cabinet.currency}</span>
        </div>
      </div>

      {cabinet.is_blocked ? (
        <div className={styles.blockedBanner}>
          Siz bloklangansiz — liniyaga chiqa olmaysiz. Sabab uchun administratsiyaga murojaat qiling.
        </div>
      ) : (
        <div className={styles.availabilityRow}>
          <div>
            <div className={styles.availabilityText}>Liniyaga chiqish</div>
            <div className={styles.availabilityHint}>
              {!cabinet.is_available && "O'chirilgan"}
              {cabinet.is_available && !isFutureAvailability && "Yoqilgan — buyurtma takliflarini olasiz"}
              {cabinet.is_available && isFutureAvailability && `${formatAvailableFrom(cabinet.available_from_date!)} dan yuk qabul qilasiz`}
            </div>
          </div>
          <button
            className={cabinet.is_available ? styles.switchOn : styles.switch}
            onClick={() => (cabinet.is_available ? handleGoOffline() : setSheetOpen(true))}
            disabled={submitting}
            aria-label="Liniyaga chiqish"
          >
            <span className={cabinet.is_available ? styles.switchKnobOn : styles.switchKnob} />
          </button>
        </div>
      )}

      {error && <div className={styles.blockedBanner}>{error}</div>}

      <div className={styles.infoBanner}>
        Yangi buyurtma takliflari hozircha Telegram bot xabarlari orqali keladi — xabar kelganda
        "✅ Qabul qilish" yoki "❌ Rad etish" tugmasini bosing. To'liq kabinet (buyurtmalar tarixi,
        xarita) tez orada qo'shiladi.
      </div>

      {sheetOpen && <GoOnlineSheet onSubmit={handleGoOnline} onClose={() => setSheetOpen(false)} submitting={submitting} />}
    </div>
  );
}
