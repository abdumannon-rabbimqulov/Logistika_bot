import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getMe, updateMe } from '../api/auth';
import { ApiError } from '../api/client';
import { listMyOrders } from '../api/orders';
import { useAuth } from '../auth/AuthProvider';
import { AccountSettingsSection } from '../components/AccountSettingsSection';
import { BottomNav } from '../components/BottomNav';
import { ChevronRightIcon, MessagesNavIcon, PhoneIcon, UserLineIcon, WalletIcon } from '../components/icons';
import type { OrderListItem, UserProfile } from '../types/api';
import { formatPrice } from '../utils/format';
import { PHONE_PLACEHOLDER } from '../utils/phone';
import styles from './ProfilePage.module.css';

export function ProfilePage() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [orders, setOrders] = useState<OrderListItem[] | null>(null);
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

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

    listMyOrders()
      .then(setOrders)
      .catch(() => setOrders([]));
  }, []);

  const stats = useMemo(() => {
    const list = orders ?? [];
    const completed = list.filter((o) => o.status === 'COMPLETED');
    const totalSpent = completed.reduce((sum, o) => sum + Number(o.price), 0);
    return { total: list.length, completedCount: completed.length, totalSpent };
  }, [orders]);

  const initials = (profile?.full_name ?? '').trim().charAt(0).toUpperCase() || 'S';
  const memberSince = profile
    ? new Date(profile.created_at).toLocaleDateString('uz-UZ', { month: 'long', year: 'numeric' })
    : null;

  async function handleSave() {
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateMe({ full_name: fullName, phone_number: phone });
      setProfile(updated);
      setSaved(true);
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Saqlanmadi');
    } finally {
      setSaving(false);
    }
  }

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await logout();
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <div className={styles.title}>Profil</div>

        {/* Bosh karta: avatar, ism, a'zolik sanasi */}
        <div className={styles.headerCard}>
          <div className={styles.avatar}>{initials}</div>
          <div className={styles.headerInfo}>
            <div className={styles.name}>{profile?.full_name || 'Foydalanuvchi'}</div>
            <div className={styles.memberSince}>{memberSince ? `${memberSince} dan beri` : '—'}</div>
          </div>
        </div>

        {/* Balans kartasi */}
        <div className={styles.balanceCard}>
          <div className={styles.balanceLabel}>Balans</div>
          <div className={styles.balanceValue}>{formatPrice(profile?.balance ?? 0)} UZS</div>
        </div>

        {/* Statistika plitkalari */}
        <div className={styles.statsRow}>
          <div className={styles.statTile}>
            <div className={styles.statValue}>{orders === null ? '—' : stats.total}</div>
            <div className={styles.statLabel}>Jami buyurtma</div>
          </div>
          <div className={styles.statTile}>
            <div className={styles.statValue}>{orders === null ? '—' : stats.completedCount}</div>
            <div className={styles.statLabel}>Yakunlangan</div>
          </div>
          <div className={styles.statTile}>
            <div className={styles.statValue}>{orders === null ? '—' : formatPrice(stats.totalSpent)}</div>
            <div className={styles.statLabel}>Jami sarflangan</div>
          </div>
        </div>

        {/* Shaxsiy ma'lumotlar */}
        <div className={styles.sectionTitle}>Shaxsiy ma'lumotlar</div>
        {!editing ? (
          <div className={styles.rows}>
            <div className={styles.row}>
              <span className={styles.rowIcon}><UserLineIcon /></span>
              <span className={styles.rowText}>
                <span className={styles.rowTitle}>Ism familiya</span>
                <span className={styles.rowSub}>{profile?.full_name || "Kiritilmagan"}</span>
              </span>
            </div>
            <div className={styles.row}>
              <span className={styles.rowIcon}><PhoneIcon color="var(--color-gray-700)" /></span>
              <span className={styles.rowText}>
                <span className={styles.rowTitle}>Telefon raqami</span>
                <span className={styles.rowSub}>{profile?.phone_number || "Kiritilmagan"}</span>
              </span>
            </div>
            <button className={styles.editRow} onClick={() => setEditing(true)}>
              <span className={styles.rowIcon}><WalletIcon /></span>
              <span className={styles.rowText}>
                <span className={styles.rowTitle}>Ma'lumotlarni tahrirlash</span>
              </span>
              <ChevronRightIcon />
            </button>
          </div>
        ) : (
          <div className={styles.editCard}>
            <div className={styles.field}>
              <label className={styles.label}>Ism familiya</label>
              <input className={styles.input} value={fullName} onChange={(e) => setFullName(e.target.value)} />
            </div>
            <div className={styles.field}>
              <label className={styles.label}>Telefon raqami</label>
              <input className={styles.input} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder={PHONE_PLACEHOLDER} inputMode="tel" />
            </div>
            {error && <div className={styles.errorHint}>{error}</div>}
            <div className={styles.editActions}>
              <button className={styles.cancelBtn} onClick={() => setEditing(false)} disabled={saving}>
                Bekor qilish
              </button>
              <button className={styles.saveBtn} disabled={saving} onClick={handleSave}>
                {saving ? 'Saqlanmoqda...' : 'Saqlash'}
              </button>
            </div>
          </div>
        )}
        {saved && <div className={styles.savedHint}>Saqlandi</div>}

        {/* Murojaatlar — haydovchi profilidagi bilan bir xil band
            (`DriverProfilePage.tsx`). Asosiy kirish yuqoridagi qo'ng'iroq tugmasi,
            bu esa profildan izlaydiganlar uchun ikkinchi yo'l. */}
        <div className={styles.rows}>
          <button className={styles.editRow} onClick={() => navigate('/messages')}>
            <span className={styles.rowIcon}><MessagesNavIcon size={20} /></span>
            <span className={styles.rowText}>
              <span className={styles.rowTitle}>Murojaatlar</span>
              <span className={styles.rowSub}>Yordam xizmatiga savol yoki shikoyat</span>
            </span>
            <ChevronRightIcon />
          </button>
        </div>

        <AccountSettingsSection />

        <button className={styles.logoutBtn} onClick={handleLogout} disabled={loggingOut}>
          {loggingOut ? 'Chiqilmoqda...' : 'Chiqish'}
        </button>
      </div>

      <BottomNav />
    </div>
  );
}
