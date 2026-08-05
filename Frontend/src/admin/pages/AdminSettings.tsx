import { useEffect, useState, type ReactNode } from 'react';
import { ApiError } from '../../api/client';
import {
  getCommissionSettings,
  getPricingSettings,
  updateCommission,
  updatePricingSettings,
} from '../../api/admin';
import shared from '../shared.module.css';
import styles from './AdminSettings.module.css';

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('uz-UZ');
}

interface PercentCardProps {
  title: string;
  description: ReactNode;
  label: string;
  /** Joriy qiymatni o'qish (GET). */
  load: () => Promise<{ percent: number; updatedAt: string }>;
  /** Yangi qiymatni saqlash (PATCH). */
  save: (percent: number) => Promise<{ percent: number; updatedAt: string }>;
  /** Kiritilgan foiz nimani anglatishini ko'rsatuvchi misol. */
  example?: (percent: number) => ReactNode;
}

/** Bitta foizli sozlama kartasi. Ikkala sozlama ham (komissiya, chegirma chegarasi)
 *  bir xil shaklda: 0–100 oralig'idagi foiz + saqlash. Shuning uchun forma mantiqi
 *  bitta joyda turadi, faqat matn va so'rov funksiyalari almashadi. */
function PercentCard({ title, description, label, load, save, example }: PercentCardProps) {
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [current, setCurrent] = useState<number | null>(null);
  const [percent, setPercent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    load()
      .then((res) => {
        if (cancelled) return;
        setCurrent(res.percent);
        setUpdatedAt(res.updatedAt);
        setPercent(String(res.percent));
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'Sozlamalar yuklanmadi');
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
    // `load` har renderga yangi funksiya bo'lishi mumkin — kartani bir marta yuklaymiz.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = Number(percent.replace(',', '.'));
  const valid = percent.trim() !== '' && Number.isFinite(value) && value >= 0 && value <= 100;
  const changed = current != null && valid && value !== Number(current);

  async function submit() {
    if (!valid || saving) return;
    setSaving(true);
    setError(null);
    try {
      const res = await save(value);
      setCurrent(res.percent);
      setUpdatedAt(res.updatedAt);
      setPercent(String(res.percent));
      setSavedAt(Date.now());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Saqlab bo'lmadi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.card}>
      <div className={styles.cardHead}>
        <h2 className={styles.cardTitle}>{title}</h2>
        <p className={styles.cardSub}>{description}</p>
      </div>

      {error && <div className={shared.errorBanner}>{error}</div>}

      {loading ? (
        <div className={styles.skeleton} />
      ) : (
        <>
          <div className={styles.formRow}>
            <label className={styles.field}>
              <span className={styles.label}>{label}</span>
              <div className={styles.inputWrap}>
                <input
                  className={styles.input}
                  inputMode="decimal"
                  value={percent}
                  onChange={(e) => {
                    setPercent(e.target.value);
                    setSavedAt(null);
                  }}
                />
                <span className={styles.suffix}>%</span>
              </div>
            </label>

            <button className={shared.primaryBtn} disabled={!changed || saving} onClick={submit}>
              {saving ? 'Saqlanmoqda...' : 'Saqlash'}
            </button>
          </div>

          {!valid && percent.trim() !== '' && (
            <div className={styles.invalid}>Foiz 0 dan 100 gacha son bo'lishi kerak</div>
          )}

          <div className={styles.meta}>
            <span>Oxirgi o'zgarish: {updatedAt ? formatDateTime(updatedAt) : '—'}</span>
            {savedAt && <span className={styles.saved}>Saqlandi ✓</span>}
          </div>

          {example && valid && <div className={styles.example}>{example(value)}</div>}
        </>
      )}
    </div>
  );
}

/** Platforma sozlamalari: komissiya foizi va sender uchun chegirma chegarasi. */
export function AdminSettings() {
  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <h1 className={shared.pageTitle}>Sozlamalar</h1>
          <div className={shared.pageSub}>Platforma komissiyasi va narx qoidalari</div>
        </div>
      </div>

      <PercentCard
        title="Komissiya foizi"
        description="Har bir yakunlangan (COMPLETED) buyurtma narxidan shu foiz haydovchi balansidan avtomatik yechiladi. Balans manfiyga tushsa haydovchi avtomatik bloklanadi."
        label="Komissiya (%)"
        load={async () => {
          const res = await getCommissionSettings();
          return { percent: Number(res.commission_percent), updatedAt: res.updated_at };
        }}
        save={async (percent) => {
          const res = await updateCommission(percent);
          return { percent: Number(res.commission_percent), updatedAt: res.updated_at };
        }}
        example={(percent) => (
          <>
            Misol: 1 000 000 UZS lik buyurtmada komissiya ={' '}
            <strong>{Math.round((1_000_000 * percent) / 100).toLocaleString('uz-UZ')} UZS</strong>
          </>
        )}
      />

      <PercentCard
        title="Sender uchun chegirma chegarasi"
        description="Sender buyurtma narxini qo'lda o'zgartirganda hisoblangan narxdan eng ko'p shuncha foizga tushira oladi. Narxni OSHIRISH cheklanmaydi — faqat pasaytirish chegaralanadi, aks holda haydovchi topilmay qolardi."
        label="Maksimal chegirma (%)"
        load={async () => {
          const res = await getPricingSettings();
          return {
            percent: Number(res.sender_max_discount_percent),
            updatedAt: res.updated_at,
          };
        }}
        save={async (percent) => {
          const res = await updatePricingSettings(percent);
          return {
            percent: Number(res.sender_max_discount_percent),
            updatedAt: res.updated_at,
          };
        }}
        example={(percent) => (
          <>
            Misol: hisoblangan narx 1 000 000 UZS bo'lsa, sender eng past{' '}
            <strong>
              {Math.round(1_000_000 * (1 - percent / 100)).toLocaleString('uz-UZ')} UZS
            </strong>{' '}
            qo'ya oladi
          </>
        )}
      />
    </div>
  );
}
