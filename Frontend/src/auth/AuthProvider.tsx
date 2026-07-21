import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { getMe, loginWithInitData } from '../api/auth';
import { clearTokens, getAccessToken, getRefreshToken, setTokens, setUnauthorizedHandler } from '../api/client';
import { getInitData } from '../telegram';
import type { UserRole } from '../types/api';

// 'guest'   — hali rol tanlanmagan, Register oqimi ko'rsatiladi
// 'sender'  — to'liq sender ilovasi
// 'driver'  — haydovchi (DriverGate o'zi profil borligini tekshiradi)
// 'unsupported' — admin/dispatcher/manager kabi Mini App uchun mo'ljallanmagan rol
type AuthStatus = 'loading' | 'guest' | 'sender' | 'driver' | 'unsupported' | 'error';

interface AuthState {
  status: AuthStatus;
  role: UserRole | null;
  userId: number | null;
  errorMessage: string | null;
  retry: () => void;
  refreshRole: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

function statusForRole(role: UserRole): AuthStatus {
  if (role === 'guest') return 'guest';
  if (role === 'sender') return 'sender';
  if (role === 'driver') return 'driver';
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
      // Refresh ham ishlamadi — tozalab, qayta Telegram init_data bilan kirishga urinamiz.
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
            throw new Error(
              "Telegram orqali ochilmagan — bu ilova faqat Telegram Mini App sifatida ishlaydi.",
            );
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

  const value = useMemo<AuthState>(
    () => ({ status, role, userId, errorMessage, retry, refreshRole }),
    [status, role, userId, errorMessage, retry, refreshRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth AuthProvider ichida ishlatilishi kerak');
  return ctx;
}
