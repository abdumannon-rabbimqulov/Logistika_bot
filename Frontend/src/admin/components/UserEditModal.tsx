import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { getUser, updateUser } from '../../api/admin';
import type { AdminUserListItem, AdminUserUpdate, UserRole } from '../../types/api';
import { Modal } from './Modal';
import shared from '../shared.module.css';
import styles from './UserEditModal.module.css';

interface Props {
  user: AdminUserListItem;
  onClose: () => void;
  onSaved: (updated: AdminUserListItem) => void;
}

const ROLES: { value: UserRole; label: string }[] = [
  { value: 'admin', label: 'Admin' },
  { value: 'sender', label: 'Yuk beruvchi' },
  { value: 'driver', label: 'Haydovchi' },
  { value: 'guest', label: 'Mehmon' },
  { value: 'dispatcher', label: 'Dispetcher' },
  { value: 'manager', label: 'Menejer' },
];

const LANGUAGES = [
  { value: 'uz', label: "O'zbekcha" },
  { value: 'ru', label: 'Русский' },
  { value: 'en', label: 'English' },
];

/** Foydalanuvchini tahrirlash — PATCH faqat o'zgargan maydonlarni yuboradi. */
export function UserEditModal({ user, onClose, onSaved }: Props) {
  // Ro'yxatdagi nusxa eskirgan bo'lishi mumkin — modal ochilganda eng oxirgi holat olinadi.
  const [source, setSource] = useState<AdminUserListItem>(user);
  const [fullName, setFullName] = useState(user.full_name ?? '');
  const [role, setRole] = useState<string>(user.role ?? 'guest');
  const [language, setLanguage] = useState(user.language ?? 'uz');
  const [isActive, setIsActive] = useState(user.is_active);
  const [isBanned, setIsBanned] = useState(user.is_banned);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getUser(user.id)
      .then((fresh) => {
        if (cancelled) return;
        setSource(fresh);
        setFullName(fresh.full_name ?? '');
        setRole(fresh.role ?? 'guest');
        setLanguage(fresh.language ?? 'uz');
        setIsActive(fresh.is_active);
        setIsBanned(fresh.is_banned);
      })
      .catch(() => {
        // Yangi holat olinmasa jadvaldagi nusxa bilan ishlayveramiz
      });
    return () => {
      cancelled = true;
    };
  }, [user.id]);

  function buildPayload(): AdminUserUpdate {
    const payload: AdminUserUpdate = {};
    if (fullName.trim() && fullName.trim() !== source.full_name) payload.full_name = fullName.trim();
    if (role !== source.role) payload.role = role as UserRole;
    if (language !== source.language) payload.language = language;
    if (isActive !== source.is_active) payload.is_active = isActive;
    if (isBanned !== source.is_banned) payload.is_banned = isBanned;
    return payload;
  }

  const payload = buildPayload();
  const dirty = Object.keys(payload).length > 0;

  async function save() {
    if (!dirty || saving) return;
    setSaving(true);
    setError(null);
    try {
      onSaved(await updateUser(source.id, payload));
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Saqlab bo'lmadi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      title={`${source.full_name || `Foydalanuvchi #${source.id}`} — tahrirlash`}
      onClose={onClose}
      footer={
        <>
          <button className={shared.ghostBtn} onClick={onClose}>
            Bekor qilish
          </button>
          <button className={shared.primaryBtn} disabled={!dirty || saving} onClick={save}>
            {saving ? 'Saqlanmoqda...' : 'Saqlash'}
          </button>
        </>
      }
    >
      <div className={styles.body}>
        <div className={styles.meta}>
          ID #{source.id}
          {source.username && ` · @${source.username}`}
          {source.phone_number && ` · ${source.phone_number}`}
        </div>

        <label className={styles.field}>
          <span className={styles.label}>To‘liq ism</span>
          <input className={styles.input} value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </label>

        <div className={styles.row}>
          <label className={styles.field}>
            <span className={styles.label}>Rol</span>
            <select className={styles.input} value={role} onChange={(e) => setRole(e.target.value)}>
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </label>

          <label className={styles.field}>
            <span className={styles.label}>Til</span>
            <select className={styles.input} value={language} onChange={(e) => setLanguage(e.target.value)}>
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>
                  {l.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className={styles.checkRow}>
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
          <span>
            Faol akkaunt
            <span className={styles.hint}>Nofaol bo‘lsa foydalanuvchi tizimga kira olmaydi</span>
          </span>
        </label>

        <label className={styles.checkRow}>
          <input type="checkbox" checked={isBanned} onChange={(e) => setIsBanned(e.target.checked)} />
          <span>
            Bloklangan
            <span className={styles.hint}>Bloklangan foydalanuvchiga token berilmaydi</span>
          </span>
        </label>

        {error && <div className={shared.errorBanner}>{error}</div>}
      </div>
    </Modal>
  );
}
