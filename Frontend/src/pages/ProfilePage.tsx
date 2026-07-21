import { useEffect, useState } from 'react';
import { getMe, updateMe } from '../api/auth';
import { ApiError } from '../api/client';
import { BottomNav } from '../components/BottomNav';
import type { UserProfile } from '../types/api';
import { formatPrice } from '../utils/format';
import styles from './ProfilePage.module.css';

export function ProfilePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getMe()
      .then((p) => {
        setProfile(p);
        setFullName(p.full_name ?? '');
        setPhone(p.phone_number ?? '');
      })
      .catch(() => {
        // profil yuklanmasa forma bo'sh qoladi, saqlash tugmasi baribir mavjud
      });
  }, []);

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateMe({ full_name: fullName, phone_number: phone });
      setProfile(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Saqlanmadi');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.topBar}>
        <div className={styles.title}>Profil</div>
      </div>

      {profile && (
        <div className={styles.section}>
          <div className={styles.balanceCard}>
            <div className={styles.balanceLabel}>Balans</div>
            <div className={styles.balanceValue}>{formatPrice(profile.balance)} UZS</div>
          </div>
        </div>
      )}

      <div className={styles.section}>
        <div className={styles.field}>
          <label className={styles.label}>Ism familiya</label>
          <input className={styles.input} value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div className={styles.field}>
          <label className={styles.label}>Telefon raqami</label>
          <input className={styles.input} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+998 XX XXX XX XX" />
        </div>
        {error && <div className={styles.savedHint} style={{ color: 'var(--color-danger)' }}>{error}</div>}
        {saved && <div className={styles.savedHint}>Saqlandi</div>}
        <button className={styles.saveBtn} disabled={saving} onClick={handleSave}>
          {saving ? 'Saqlanmoqda...' : 'Saqlash'}
        </button>
      </div>

      <BottomNav />
    </div>
  );
}
