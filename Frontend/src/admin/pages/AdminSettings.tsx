import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { getCommissionSettings, updateCommission } from '../../api/admin';
import type { CommissionSettings } from '../../types/api';
import shared from '../shared.module.css';
import styles from './AdminSettings.module.css';

function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('uz-UZ');
}

/** Platforma sozlamalari — hozircha komissiya foizi (GET/PATCH /system/settings/commission). */
export function AdminSettings() {
  const [settings, setSettings] = useState<CommissionSettings | null>(null);
  const [percent, setPercent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    getCommissionSettings()
      .then((res) => {
        if (cancelled) return;
        setSettings(res);
        setPercent(String(res.commission_percent));
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'Sozlamalar yuklanmadi');
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  const value = Number(percent.replace(',', '.'));
  const valid = percent.trim() !== '' && Number.isFinite(value) && value >= 0 && value <= 100;
  const changed = settings != null && valid && value !== Number(settings.commission_percent);

  async function save() {
    if (!valid || saving) return;
    setSaving(true);
    setError(null);
    try {
      const res = await updateCommission(value);
      setSettings(res);
      setPercent(String(res.commission_percent));
      setSavedAt(Date.now());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Saqlab bo'lmadi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <h1 className={shared.pageTitle}>Sozlamalar</h1>
          <div className={shared.pageSub}>Platforma komissiyasi va to'lov qoidalari</div>
        </div>
      </div>

      {error && <div className={shared.errorBanner}>{error}</div>}

      <div className={styles.card}>
        <div className={styles.cardHead}>
          <h2 className={styles.cardTitle}>Komissiya foizi</h2>
          <p className={styles.cardSub}>
            Har bir yakunlangan (COMPLETED) buyurtma narxidan shu foiz haydovchi balansidan
            avtomatik yechiladi. Balans manfiyga tushsa haydovchi avtomatik bloklanadi.
          </p>
        </div>

        {loading ? (
          <div className={styles.skeleton} />
        ) : (
          <>
            <div className={styles.formRow}>
              <label className={styles.field}>
                <span className={styles.label}>Komissiya (%)</span>
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

              <button className={shared.primaryBtn} disabled={!changed || saving} onClick={save}>
                {saving ? 'Saqlanmoqda...' : 'Saqlash'}
              </button>
            </div>

            {!valid && percent.trim() !== '' && (
              <div className={styles.invalid}>Foiz 0 dan 100 gacha son bo'lishi kerak</div>
            )}

            <div className={styles.meta}>
              <span>Oxirgi o'zgarish: {settings ? formatDateTime(settings.updated_at) : '—'}</span>
              {savedAt && <span className={styles.saved}>Saqlandi ✓</span>}
            </div>

            {settings && valid && (
              <div className={styles.example}>
                Misol: 1 000 000 UZS lik buyurtmada komissiya ={' '}
                <strong>{Math.round((1_000_000 * value) / 100).toLocaleString('uz-UZ')} UZS</strong>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
