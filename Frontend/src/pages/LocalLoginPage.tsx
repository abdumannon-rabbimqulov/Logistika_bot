import { useState } from 'react';
import { requestPasswordResetCode, setNewPassword, verifyPasswordResetCode } from '../api/auth';
import { ApiError } from '../api/client';
import { useAuth } from '../auth/AuthProvider';
import styles from './LocalLoginPage.module.css';

type Step = 'login' | 'request-code' | 'verify-code' | 'set-password' | 'done';

// Telegram init_data yo'q holatda (oddiy brauzer/local manzil) ko'rsatiladi — backendda
// allaqachon mavjud telefon+parol oqimidan foydalanadi (users/router.py). Yangi
// akkauntlar Telegram orqali yaratilgani uchun parol hali yo'q — shuning uchun
// "Parol o'rnatish" (mavjud reset-phone/verify-reset-code/reset-password endpointlari,
// kod Telegramga yuboriladi) ham shu yerga qo'shilgan.
export function LocalLoginPage() {
  const { loginWithPhone } = useAuth();
  const [step, setStep] = useState<Step>('login');

  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPasswordValue] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetToken, setResetToken] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  async function handleLogin() {
    setSubmitting(true);
    setError(null);
    try {
      await loginWithPhone(phone.trim(), password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Kirishda xato');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRequestCode() {
    if (!phone.trim()) {
      setError('Telefon raqamini kiriting');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const res = await requestPasswordResetCode(phone.trim());
      setInfo(res.detail);
      setStep('verify-code');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Kod yuborilmadi');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerifyCode() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await verifyPasswordResetCode(phone.trim(), code.trim());
      setResetToken(res.reset_token);
      setInfo(null);
      setStep('set-password');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Kod noto'g'ri");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSetPassword() {
    if (newPassword.length < 8) {
      setError("Parol kamida 8 belgidan iborat bo'lishi kerak");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Parollar mos kelmadi');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await setNewPassword(resetToken, newPassword, confirmPassword);
      setPassword('');
      setInfo("Parol o'rnatildi — endi shu parol bilan kiring");
      setStep('login');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Parol saqlanmadi');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.title}>YUK</div>
      <div className={styles.subtitle}>
        {step === 'login' && "Telegram tashqarisida ochdingiz — telefon raqami va parol bilan kiring."}
        {step === 'request-code' && "Parol o'rnatish uchun Telegram akkauntingizga tasdiqlash kodi yuboramiz."}
        {step === 'verify-code' && 'Telegramga kelgan kodni kiriting.'}
        {step === 'set-password' && 'Yangi parolingizni o\'rnating.'}
      </div>

      {step === 'login' && (
        <>
          <div className={styles.field}>
            <label className={styles.label}>Telefon raqami</label>
            <input className={styles.input} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+998 XX XXX XX XX" inputMode="tel" />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Parol</label>
            <input className={styles.input} type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {error && <div className={styles.error}>{error}</div>}
          {info && <div className={styles.success}>{info}</div>}
          <button className={styles.submitBtn} disabled={submitting} onClick={handleLogin}>
            {submitting ? 'Kirilmoqda...' : 'Kirish'}
          </button>
          <button className={styles.linkBtn} onClick={() => { setStep('request-code'); setError(null); setInfo(null); }}>
            Parolni unutdingizmi yoki birinchi marta kirasizmi?
          </button>
        </>
      )}

      {step === 'request-code' && (
        <>
          <div className={styles.field}>
            <label className={styles.label}>Telefon raqami</label>
            <input className={styles.input} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+998 XX XXX XX XX" inputMode="tel" />
          </div>
          {error && <div className={styles.error}>{error}</div>}
          <button className={styles.submitBtn} disabled={submitting} onClick={handleRequestCode}>
            {submitting ? 'Yuborilmoqda...' : 'Kod yuborish'}
          </button>
          <button className={styles.linkBtn} onClick={() => { setStep('login'); setError(null); }}>
            Ortga
          </button>
        </>
      )}

      {step === 'verify-code' && (
        <>
          {info && <div className={styles.success}>{info}</div>}
          <div className={styles.field}>
            <label className={styles.label}>Tasdiqlash kodi</label>
            <input className={styles.input} value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" />
          </div>
          {error && <div className={styles.error}>{error}</div>}
          <button className={styles.submitBtn} disabled={submitting} onClick={handleVerifyCode}>
            {submitting ? 'Tekshirilmoqda...' : 'Tasdiqlash'}
          </button>
        </>
      )}

      {step === 'set-password' && (
        <>
          <div className={styles.field}>
            <label className={styles.label}>Yangi parol</label>
            <input className={styles.input} type="password" value={newPassword} onChange={(e) => setNewPasswordValue(e.target.value)} />
          </div>
          <div className={styles.field}>
            <label className={styles.label}>Parolni tasdiqlang</label>
            <input className={styles.input} type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
          </div>
          {error && <div className={styles.error}>{error}</div>}
          <button className={styles.submitBtn} disabled={submitting} onClick={handleSetPassword}>
            {submitting ? 'Saqlanmoqda...' : 'Parolni saqlash'}
          </button>
        </>
      )}

      <div className={styles.hint}>
        Bu ilova asosan Telegram Mini App sifatida mo'ljallangan — to'liq tajriba uchun botdagi
        "Yuk ilovasi" tugmasidan foydalaning.
      </div>
    </div>
  );
}
