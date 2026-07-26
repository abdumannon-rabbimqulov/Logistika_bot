import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { getMe, loginWithInitData, loginWithPassword, logout as logoutRequest } from '../api/auth';
import { clearTokens, getAccessToken, getRefreshToken, setTokens, setUnauthorizedHandler } from '../api/client';
import { getInitData } from '../telegram';
import type { UserRole } from '../types/api';

// 'local-login' — Telegram init_data yo'q (oddiy brauzer/local manzildan ochilgan) —
//                 telefon+parol bilan kirish formasi ko'rsatiladi
// 'guest'   — hali rol tanlanmagan, Register oqimi ko'rsatiladi
// 'sender'  — to'liq sender ilovasi
// 'driver'  — haydovchi (DriverGate o'zi profil borligini tekshiradi)
// 'admin'   — desktop admin panel (Mini App emas, alohida to'liq ekran)
// 'unsupported' — dispatcher/manager kabi Mini App uchun mo'ljallanmagan rol
type AuthStatus = 'loading' | 'local-login' | 'guest' | 'sender' | 'driver' | 'admin' | 'unsupported' | 'error';

interface AuthState {
  status: AuthStatus;
  role: UserRole | null;
  userId: number | null;
  errorMessage: string | null;
  retry: () => void;
  refreshRole: () => Promise<void>;
  loginWithPhone: (phone: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

function statusForRole(role: UserRole): AuthStatus {
  if (role === 'guest') return 'guest';
  if (role === 'sender') return 'sender';
  if (role === 'driver') return 'driver';
  if (role === 'admin') return 'admin';
  return 'unsupported';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [role, setRole] = useState<UserRole | null>(null);
  const [userId, setUserId] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      // Refresh ham ishlamadi — tozalab, qayta kirishga urinamiz (init_data yoki local-login).
      setStatus('loading');
      setAttempt((n) => n + 1);
    });
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function authenticate() {
      setStatus('loading');
      setErrorMessage(null);
      try {
        if (!getAccessToken() || !getRefreshToken()) {
          const initData = getInitData();
          if (!initData) {
            // Telegram tashqarisida ochilgan (masalan lokal http://localhost:5173) —
            // xato bermasdan telefon+parol bilan kirish formasini ko'rsatamiz.
            setStatus('local-login');
            return;
          }
          const login = await loginWithInitData(initData);
          if (cancelled) return;
          setTokens(login.access_token, login.refresh_token);
          setRole(login.role);
          setUserId(login.user_id);
          setStatus(statusForRole(login.role));
          return;
        }

        // Tokenlar bor (oldingi sessiyadan) — role hali noma'lum, shuning uchun tasdiqlash
        // uchun profilni so'raymiz (rol bot orqali o'zgargan bo'lishi ham mumkin).
        const me = await getMe();
        if (cancelled) return;
        setRole(me.role as UserRole);
        setUserId(me.id);
        setStatus(statusForRole(me.role as UserRole));
      } catch (err) {
        if (cancelled) return;
        clearTokens();
        setErrorMessage(err instanceof Error ? err.message : "Kirishda noma'lum xato");
        setStatus('error');
      }
    }

    void authenticate();
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  // Register/rol tanlashdan keyin qayta so'ramasdan holatni yangilash uchun.
  const refreshRole = useCallback(async () => {
    const me = await getMe();
    setRole(me.role as UserRole);
    setUserId(me.id);
    setStatus(statusForRole(me.role as UserRole));
  }, []);

  // 'local-login' ekranidan (LocalLoginPage) chaqiriladi — Telegram init_data'ga
  // muqobil, backendda allaqachon mavjud telefon+parol oqimi.
  const loginWithPhone = useCallback(async (phone: string, password: string) => {
    const login = await loginWithPassword(phone, password);
    setTokens(login.access_token, login.refresh_token);
    setRole(login.role);
    setUserId(login.user_id);
    setStatus(statusForRole(login.role));
  }, []);

  // Profildan "Chiqish" tugmasi chaqiradi — backendga logout so'rovi (refresh token bekor
  // qilinadi) yuboriladi, natijasidan qat'iy nazar tokenlar tozalanadi va qayta autentifikatsiya
  // effekti ishga tushadi (init_data yoki local-login oqimiga tushadi).
  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // token allaqachon yaroqsiz bo'lishi mumkin — baribir lokal holatni tozalaymiz
    }
    clearTokens();
    setRole(null);
    setUserId(null);
    setStatus('loading');
    setAttempt((n) => n + 1);
  }, []);

  const value = useMemo<AuthState>(
    () => ({ status, role, userId, errorMessage, retry, refreshRole, loginWithPhone, logout }),
    [status, role, userId, errorMessage, retry, refreshRole, loginWithPhone, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth AuthProvider ichida ishlatilishi kerak');
  return ctx;
}
