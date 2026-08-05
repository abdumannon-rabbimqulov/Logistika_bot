import { useState } from 'react';
import { changePassword, deleteAccount } from '../api/auth';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import { BottomSheetModal } from './BottomSheetModal';
import styles from './AccountSettingsSection.module.css';

// Parolni o'zgartirish va akkauntni o'chirish. Ikkala ekranda ham (sender profili va
// haydovchi profili) bir xil bo'lgani uchun alohida komponentga chiqarilgan.

// Backend cheklovi (users/schemas.py ChangePasswordRequest).
const MIN_PASSWORD_LENGTH = 8;

function ChangePasswordSheet({ onClose }: { onClose: () => void }) {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  const mismatch = confirm.length > 0 && newPassword !== confirm;
  const valid =
    oldPassword.length > 0 && newPassword.length >= MIN_PASSWORD_LENGTH && !mismatch && confirm.length > 0;

  async function save() {
    if (!valid || saving) return;
    setSaving(true);
    setError(null);
    try {
      await changePassword(oldPassword, newPassword);
      setDone(true);
    } catch (err) {
      // Eski parol noto'g'ri bo'lsa backend 400 va aniq sabab qaytaradi.
      setError(err instanceof ApiError ? err.message : "Parolni o'zgartirib bo'lmadi");
    } finally {
      setSaving(false);
    }
  }

  return (
    <BottomSheetModal title="Parolni o'zgartirish" onClose={onClose}>
      <div className={styles.form}>
        {done ? (
          <>
            <div className={styles.success}>Parol muvaffaqiyatli o'zgartirildi</div>
            <button className={styles.submit} onClick={onClose}>
              Yopish
            </button>
          </>
        ) : (
          <>
            {error && <div className={styles.error}>{error}</div>}

            <label className={styles.field}>
              <span className={styles.label}>Joriy parol</span>
              <input
                className={styles.input}
                type="password"
                value={oldPassword}
                autoComplete="current-password"
                onChange={(e) => setOldPassword(e.target.value)}
              />
            </label>

            <label className={styles.field}>
              <span className={styles.label}>Yangi parol</span>
              <input
                className={styles.input}
                type="password"
                value={newPassword}
                autoComplete="new-password"
                onChange={(e) => setNewPassword(e.target.value)}
              />
              {newPassword.length > 0 && newPassword.length < MIN_PASSWORD_LENGTH && (
                <span className={styles.invalid}>
                  Kamida {MIN_PASSWORD_LENGTH} ta belgi bo'lishi kerak
                </span>
              )}
            </label>

            <label className={styles.field}>
              <span className={styles.label}>Yangi parolni takrorlang</span>
              <input
                className={styles.input}
                type="password"
                value={confirm}
                autoComplete="new-password"
                onChange={(e) => setConfirm(e.target.value)}
              />
              {mismatch && <span className={styles.invalid}>Parollar mos kelmadi</span>}
            </label>

            <button className={styles.submit} disabled={!valid || saving} onClick={save}>
              {saving ? 'Saqlanmoqda...' : "O'zgartirish"}
            </button>
          </>
        )}
      </div>
    </BottomSheetModal>
  );
}

function DeleteAccountSheet({ onClose }: { onClose: () => void }) {
  const { logout } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirmDelete() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await deleteAccount();
      // Server akkauntni deaktivatsiya qildi — endi mavjud tokenlar bilan ishlash
      // ma'nosiz, shuning uchun to'liq chiqib, autentifikatsiya oqimini qaytadan
      // boshlaymiz (logout tokenlarni ham tozalaydi).
      await logout();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Akkauntni o'chirib bo'lmadi");
      setBusy(false);
    }
  }

  return (
    <BottomSheetModal title="Akkauntni o'chirish" onClose={onClose}>
      <div className={styles.form}>
        {error && <div className={styles.error}>{error}</div>}

        <div className={styles.warning}>
          Akkaunt o'chirilgach tizimga kira olmaysiz. Buyurtmalar tarixi hisobot uchun
          saqlanib qoladi. Qaytadan foydalanmoqchi bo'lsangiz, yordam xizmatiga murojaat
          qilishingiz kerak bo'ladi.
        </div>

        <button className={styles.dangerBtn} disabled={busy} onClick={confirmDelete}>
          {busy ? "O'chirilmoqda..." : "Ha, akkauntni o'chirish"}
        </button>
        <button className={styles.ghostBtn} disabled={busy} onClick={onClose}>
          Bekor qilish
        </button>
      </div>
    </BottomSheetModal>
  );
}

export function AccountSettingsSection() {
  const [sheet, setSheet] = useState<'password' | 'delete' | null>(null);

  return (
    <div className={styles.section}>
      <div className={styles.sectionTitle}>Xavfsizlik</div>

      <button className={styles.rowBtn} onClick={() => setSheet('password')}>
        Parolni o'zgartirish
      </button>

      <button className={styles.rowBtnDanger} onClick={() => setSheet('delete')}>
        Akkauntni o'chirish
      </button>

      {sheet === 'password' && <ChangePasswordSheet onClose={() => setSheet(null)} />}
      {sheet === 'delete' && <DeleteAccountSheet onClose={() => setSheet(null)} />}
    </div>
  );
}
