import { useEffect, useMemo, useState } from 'react';
import { ApiError } from '../api/client';
import { listMyEarnings } from '../api/drivers';
import { DriverBottomNav } from '../components/DriverBottomNav';
import { StarIcon } from '../components/icons';
import type { DriverEarning } from '../types/api';
import { formatPrice } from '../utils/format';
import { useDriverCabinet } from './DriverCabinetContext';
import styles from './DriverEarningsPage.module.css';

const DAY_LABELS = ['Du', 'Se', 'Ch', 'Pa', 'Ju', 'Sh', 'Ya']; // Dushanba..Yakshanba
// Ro'yxatda va haftalik grafikda ishlatiladigan yozuvlar soni.
const EARNINGS_LIMIT = 50;

interface DayBucket {
  label: string;
  total: number;
}

// Buyurtma daromadi YAKUNLANGAN sana bo'yicha hisoblanadi (created_at emas): 10 kun
// oldin yaratilib bugun yakunlangan yuk aynan shu haftaga tegishli. Eski yozuvlarda
// completed_at NULL bo'lishi mumkin — ular haftalik hisobga qo'shilmaydi.
function completionDate(item: DriverEarning): Date | null {
  if (!item.completed_at) return null;
  const d = new Date(item.completed_at);
  return Number.isNaN(d.getTime()) ? null : d;
}

// Oxirgi 7 kunni (bugundan orqaga) Dushanba-boshli hafta indeksiga joylaydi.
function buildWeek(completed: DriverEarning[]): { buckets: DayBucket[]; weekTotal: number; weekCount: number } {
  const now = new Date();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);
  start.setDate(start.getDate() - 6); // 7 kunlik oyna (bugun + oldingi 6 kun)

  const buckets: DayBucket[] = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    const weekday = (d.getDay() + 6) % 7; // 0=Dushanba
    return { label: DAY_LABELS[weekday], total: 0 };
  });

  let weekTotal = 0;
  let weekCount = 0;
  for (const item of completed) {
    const done = completionDate(item);
    if (!done) continue;
    const dayIndex = Math.floor((done.getTime() - start.getTime()) / 86_400_000);
    if (dayIndex >= 0 && dayIndex < 7) {
      // Grafikda SOF daromad ko'rsatiladi (komissiya ayrilgan) — pastdagi ro'yxat
      // bilan bir xil raqam bo'lsin, aks holda "shu hafta" summasi qo'lga tushgan
      // puldan katta ko'rinib, chalg'itardi.
      buckets[dayIndex].total += Number(item.net_amount);
      weekTotal += Number(item.net_amount);
      weekCount += 1;
    }
  }
  return { buckets, weekTotal, weekCount };
}

/** Sana + vaqt: "12-noyabr, 14:30". */
function formatCompletedAt(item: DriverEarning): string {
  const done = completionDate(item);
  if (!done) return 'Sana noma’lum';
  return `${done.toLocaleDateString('uz-UZ', { day: 'numeric', month: 'long' })}, ${done.toLocaleTimeString(
    'uz-UZ',
    { hour: '2-digit', minute: '2-digit' },
  )}`;
}

export function DriverEarningsPage() {
  const { cabinet } = useDriverCabinet();
  // Server allaqachon YAKUNLANGAN buyurtmalarni, yakunlanish sanasi bo'yicha
  // saralab beradi va har biriga komissiyani bog'laydi — bu yerda filtrlash/saralash
  // kerak emas (ilgari hammasi `listMyOrders` dan olinib, komissiya umuman yo'q edi).
  const [earnings, setEarnings] = useState<DriverEarning[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMyEarnings({ limit: EARNINGS_LIMIT })
      .then(setEarnings)
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : 'Ma’lumot yuklanmadi');
        setEarnings([]);
      });
  }, []);

  // `earnings ?? []` to'g'ridan-to'g'ri yozilsa har renderda yangi massiv bo'lib,
  // quyidagi `useMemo` hech qachon keshdan foydalanmasdi.
  const completed = useMemo(() => earnings ?? [], [earnings]);
  const { buckets, weekTotal, weekCount } = useMemo(() => buildWeek(completed), [completed]);
  const maxBucket = Math.max(1, ...buckets.map((b) => b.total));
  const recent = completed.slice(0, 8);

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <div className={styles.title}>Daromad</div>

        {error && <div className={styles.errorBanner}>{error}</div>}

        {/* Haftalik daromad grafigi (qora karta, yashil ustunlar) */}
        <div className={styles.chartCard}>
          <div className={styles.chartHeaderLabel}>Shu hafta</div>
          <div className={styles.chartTotal}>
            {formatPrice(weekTotal)} <span className={styles.chartCurrency}>{cabinet.currency}</span>
          </div>
          <div className={styles.chart}>
            {buckets.map((b, i) => (
              <div key={i} className={styles.barCol}>
                <div className={styles.barTrack}>
                  <div
                    className={styles.bar}
                    style={{ height: `${Math.max(4, (b.total / maxBucket) * 100)}%` }}
                  />
                </div>
                <span className={styles.barLabel}>{b.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Statistika plitkalari */}
        <div className={styles.statsRow}>
          <div className={styles.statTile}>
            <div className={styles.statValue}>{weekCount}</div>
            <div className={styles.statLabel}>Shu hafta safar</div>
          </div>
          <div className={styles.statTile}>
            <div className={styles.statValue}>{completed.length}</div>
            <div className={styles.statLabel}>Jami yakunlangan</div>
          </div>
          <div className={styles.statTile}>
            <div className={styles.statValueRating}>
              <StarIcon size={15} /> {cabinet.rating.toFixed(1)}
            </div>
            <div className={styles.statLabel}>O'rtacha reyting</div>
          </div>
        </div>

        {/* Oxirgi to'lovlar */}
        <div className={styles.sectionTitle}>Oxirgi to'lovlar</div>
        {earnings === null ? (
          <div className={styles.spinner} />
        ) : recent.length === 0 ? (
          <div className={styles.empty}>Hali yakunlangan buyurtma yo'q</div>
        ) : (
          <div className={styles.payList}>
            {recent.map((item) => (
              <div key={item.order_id} className={styles.payRow}>
                <div className={styles.payHead}>
                  <div className={styles.payInfo}>
                    <div className={styles.payCargo}>
                      {item.cargo_name}
                      <span className={styles.payOrderId}>#{item.order_id}</span>
                    </div>
                    {(item.origin_address || item.destination_address) && (
                      <div className={styles.payRoute}>
                        {item.origin_address ?? '?'} → {item.destination_address ?? '?'}
                      </div>
                    )}
                    <div className={styles.payDate}>{formatCompletedAt(item)}</div>
                  </div>
                  {/* Asosiy raqam — haydovchi qo'liga tushgan SOF summa. */}
                  <div className={styles.payAmount}>
                    +{formatPrice(item.net_amount)} {item.currency}
                  </div>
                </div>

                {/* Hisob-kitobning ochiq ko'rinishi: buyurtma narxi va undan
                    ushlab qolingan komissiya. Komissiya 0 bo'lsa qator ko'rsatilmaydi
                    (masalan tizim ishga tushishidan oldin yakunlangan buyurtmalar). */}
                <div className={styles.payBreakdown}>
                  <span className={styles.payBreakdownItem}>
                    Buyurtma: {formatPrice(item.gross_amount)}
                  </span>
                  {Number(item.commission_amount) > 0 && (
                    <span className={styles.payCommission}>
                      Komissiya: −{formatPrice(item.commission_amount)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <DriverBottomNav />
    </div>
  );
}
