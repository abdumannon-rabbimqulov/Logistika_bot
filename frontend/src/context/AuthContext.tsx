import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { AuthSession, LoginResult } from "../types/auth";
import type { User, UserUpdateData } from "../types";
import { apiRequest } from "../api";
import { formatPhoneForApi } from "../utils/phone";
import {
  clearAuthSession,
  loadAuthSession,
  markProfileComplete,
  persistAuthSession,
  sessionFromLoginResponse,
} from "../auth/session";
import { getPostLoginPath } from "../auth/redirect";
import { getTelegramInitData, initTelegramWebApp, isTelegramWebApp } from "../auth/telegram";
import { fetchMeApi, loginApi, logoutApi, updateMeApi } from "../services/authApi";

interface AuthContextType {
  user: User | null;
  session: AuthSession | null;
  loading: boolean;
  isAuthenticated: boolean;
  isTelegramApp: boolean;
  login: (
    phone_number?: string,
    password?: string,
    initData?: string
  ) => Promise<LoginResult>;
  loginWithTelegram: () => Promise<LoginResult | null>;
  logout: () => Promise<void>;
  resetPhone: (phone_number: string) => Promise<any>;
  verifyResetCode: (code: string) => Promise<any>;
  resetPassword: (password: string, confirm: string) => Promise<any>;
  updateProfile: (data: UserUpdateData) => Promise<User>;
  refreshMe: () => Promise<User>;
  completeDriverProfile: () => void;
  getRedirectPath: () => string;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [isTelegramApp] = useState(isTelegramWebApp);

  const applySession = useCallback((next: AuthSession | null) => {
    setSession(next);
    if (next) {
      persistAuthSession(next);
    } else {
      clearAuthSession();
    }
  }, []);

  const fetchProfile = useCallback(async (): Promise<User | null> => {
    try {
      const profile = await fetchMeApi();
      setUser(profile);
      if (profile.role) {
        localStorage.setItem("logistika_user_role", profile.role);
      }
      return profile;
    } catch (err) {
      console.error("Failed to fetch profile:", err);
      applySession(null);
      setUser(null);
      return null;
    }
  }, [applySession]);

  const finalizeLogin = useCallback(
    async (data: Awaited<ReturnType<typeof loginApi>>): Promise<LoginResult> => {
      const nextSession = sessionFromLoginResponse(data);
      applySession(nextSession);

      if (nextSession.status !== "need_driver_profile") {
        await fetchProfile();
      } else {
        setUser(null);
      }

      const redirectTo = getPostLoginPath(nextSession.role, nextSession.status);
      return {
        session: nextSession,
        redirectTo,
        message: data.message,
      };
    },
    [applySession, fetchProfile]
  );

  const login = useCallback(
    async (phone_number?: string, password?: string, initData?: string): Promise<LoginResult> => {
      setLoading(true);
      try {
        const payload: Record<string, string> = {};
        if (initData) {
          payload.init_data = initData;
        } else {
          if (!phone_number || !password) {
            throw new Error("Telefon raqami va parol kerak.");
          }
          payload.phone_number = formatPhoneForApi(phone_number);
          payload.password = password;
        }

        const data = await loginApi(payload);
        return await finalizeLogin(data);
      } catch (err) {
        applySession(null);
        setUser(null);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [applySession, finalizeLogin]
  );

  const loginWithTelegram = useCallback(async (): Promise<LoginResult | null> => {
    const initData = getTelegramInitData();
    if (!initData) return null;
    initTelegramWebApp();
    return login(undefined, undefined, initData);
  }, [login]);

  useEffect(() => {
    const bootstrap = async () => {
      const stored = loadAuthSession();
      if (!stored) {
        setLoading(false);
        return;
      }
      applySession(stored);

      if (stored.status === "need_driver_profile") {
        setLoading(false);
        return;
      }

      await fetchProfile();
      setLoading(false);
    };

    bootstrap();

    const handleSessionExpired = () => {
      applySession(null);
      setUser(null);
    };
    window.addEventListener("auth_session_expired", handleSessionExpired);
    return () => window.removeEventListener("auth_session_expired", handleSessionExpired);
  }, [applySession, fetchProfile]);

  const logout = async () => {
    try {
      const refreshToken = session?.refreshToken ?? localStorage.getItem("logistika_refresh_token");
      if (refreshToken) {
        await logoutApi(refreshToken);
      }
    } catch (err) {
      console.warn("Logout request failed:", err);
    } finally {
      applySession(null);
      setUser(null);
    }
  };

  const resetPhone = async (phone_number: string) => {
    const res = await apiRequest<{ detail: string; access_token: string }>("/auth/reset-phone", {
      method: "POST",
      body: JSON.stringify({ phone_number: formatPhoneForApi(phone_number) }),
      skipAuth: true,
    });
    localStorage.setItem("logistika_access_token", res.access_token);
    return res;
  };

  const verifyResetCode = async (code: string) => {
    return apiRequest<{ detail: string }>("/auth/verify-reset-code", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
  };

  const resetPassword = async (password: string, confirm: string) => {
    const res = await apiRequest<{ detail: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ new_password: password, confirm_password: confirm }),
    });
    localStorage.removeItem("logistika_access_token");
    return res;
  };

  const updateProfile = async (data: UserUpdateData) => {
    const updated = await updateMeApi(data);
    setUser(updated);
    return updated;
  };

  const refreshMe = async () => {
    const updated = await fetchMeApi();
    setUser(updated);
    return updated;
  };

  const completeDriverProfile = () => {
    markProfileComplete();
    if (session) {
      const next = { ...session, status: "active" as const };
      applySession(next);
    }
  };

  const getRedirectPath = () => getPostLoginPath(session?.role ?? "guest", session?.status);

  const isAuthenticated = Boolean(session?.accessToken);

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        isAuthenticated,
        isTelegramApp,
        login,
        loginWithTelegram,
        logout,
        resetPhone,
        verifyResetCode,
        resetPassword,
        updateProfile,
        refreshMe,
        completeDriverProfile,
        getRedirectPath,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
