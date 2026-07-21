import { useState } from 'react';
import { selectRole, updateMe } from '../api/auth';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import { getTelegramUser } from '../telegram';
import styles from './RegisterPage.module.css';

const LANGUAGES: { code: string; label: string }[] = [
  { code: 'uz', label: "O'zbekcha" },
  { code: 'uz_cyrl', label: 'Ўзбекча' },
  { code: 'ru', label: 'Русский' },
];

type RoleChoice = 'sender' | 'driver';

// Dizaynda register ekrani yo'q — backendda GUEST -> sender/driver o'tishi uchun
// hech qanday UI umuman bo'lmagani sababli (faqat bot orqali mavjud edi), shu forma
// umumiy (ikkala rol uchun ham) ro'yxatdan o'tishni ta'minlaydi.
export function RegisterPage() {
  const { refreshRole } = useAuth();
  const tgUser = getTelegramUser();

  const [fullName, setFullName] = useState(
    tgUser ? [tgUser.first_name, tgUser.last_name].filter(Boolean).join(' ') : '',
  );
  const [phone, setPhone] = useState('');
  const [language, setLanguage] = useState(tgUser?.language_code === 'ru' ? 'ru' : 'uz');
  const [role, setRole] = useState<RoleChoice | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    if (!fullName.trim()) {
      setError('Ism familiyangizni kiriting');
      return;
    }
    if (!phone.trim()) {
      setError('Telefon raqamingizni kiriting');
      return;
    }
    if (!role) {
      setError('Rolni tanlang');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await updateMe({ full_name: fullName.trim(), phone_number: phone.trim(), language });
      await selectRole(role);
      await refreshRole();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ro'yxatdan o'tishda xato yuz berdi");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.title}>Ro'yxatdan o'tish</div>
      <div className={styles.subtitle}>Davom etish uchun ma'lumotlaringizni to'ldiring</div>

      <div className={styles.field}>
        <label className={styles.label}>Ism familiya</label>
        <input className={styles.input} value={fullName} onChange={(e) => setFullName(e.target.value)} />
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Telefon raqami</label>
        <input
          className={styles.input}
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="+998 XX XXX XX XX"
          inputMode="tel"
        />
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Til</label>
        <div className={styles.langRow}>
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              className={language === l.code ? styles.langBtnActive : styles.langBtn}
              onClick={() => setLanguage(l.code)}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.field}>
        <label className={styles.label}>Kim sifatida davom etasiz?</label>
        <div className={styles.roleRow}>
          <button className={role === 'sender' ? styles.roleCardActive : styles.roleCard} onClick={() => setRole('sender')}>
            <span className={styles.roleEmoji}>📦</span>
            <div>
              <div className={styles.roleTitle}>Yuk beruvchi</div>
              <div className={styles.roleHint}>Yuk jo'natish uchun buyurtma beraman</div>
            </div>
          </button>
          <button className={role === 'driver' ? styles.roleCardActive : styles.roleCard} onClick={() => setRole('driver')}>
            <span className={styles.roleEmoji}>🚛</span>
            <div>
              <div className={styles.roleTitle}>Haydovchi</div>
              <div className={styles.roleHint}>Yuk tashib pul topaman</div>
            </div>
          </button>
        </div>
      </div>

      {error && <div className={styles.error}>{error}</div>}

      <button className={styles.submitBtn} disabled={submitting} onClick={handleSubmit}>
        {submitting ? 'Yuborilmoqda...' : 'Davom etish'}
      </button>
    </div>
  );
}
