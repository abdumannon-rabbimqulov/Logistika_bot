import React, { createContext, useContext, useState, useEffect } from "react";
import { UserRole } from "../types";
import type { User, UserUpdateData } from "../types";
import { apiRequest } from "../api";
import { formatPhoneForApi } from "../utils/phone";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (phone_number?: string, password?: string, initData?: string) => Promise<any>;
  logout: () => Promise<void>;
  resetPhone: (phone_number: string) => Promise<any>;
  verifyResetCode: (code: string) => Promise<any>;
  resetPassword: (password: string, confirm: string) => Promise<any>;
  updateProfile: (data: UserUpdateData) => Promise<User>;
  refreshMe: () => Promise<User>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchProfile = async (): Promise<User | null> => {
    try {
      const profile = await apiRequest<User>("/auth/me");
      setUser(profile);
      if (profile.role) {
        localStorage.setItem("logistika_user_role", profile.role);
      }
      return profile;
    } catch (err) {
      console.error("Failed to fetch profile:", err);
      // Clean tokens if profile call fails
      localStorage.removeItem("logistika_access_token");
      localStorage.removeItem("logistika_refresh_token");
      localStorage.removeItem("logistika_user_role");
      setUser(null);
      return null;
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem("logistika_access_token");
      if (token) {
        await fetchProfile();
      }
      setLoading(false);
    };

    initAuth();

    // Listen for custom event triggered by apiRequest interceptor
    const handleSessionExpired = () => {
      setUser(null);
    };

    window.addEventListener("auth_session_expired", handleSessionExpired);
    return () => {
      window.removeEventListener("auth_session_expired", handleSessionExpired);
    };
  }, []);

  const login = async (phone_number?: string, password?: string, initData?: string) => {
    setLoading(true);
    try {
      const payload: any = {};
      if (initData) {
        payload.init_data = initData;
      } else {
        payload.phone_number = phone_number ? formatPhoneForApi(phone_number) : phone_number;
        payload.password = password;
      }

      const data = await apiRequest<{
        access_token: string;
        refresh_token: string;
        role: UserRole;
        user_id: number;
        status?: string;
        message?: string;
      }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(payload),
        skipAuth: true,
      });

      localStorage.setItem("logistika_access_token", data.access_token);
      localStorage.setItem("logistika_refresh_token", data.refresh_token);
      localStorage.setItem("logistika_user_role", data.role);

      const profile = await fetchProfile();
      return { success: true, data, profile };
    } catch (err: any) {
      setUser(null);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      const refreshToken = localStorage.getItem("logistika_refresh_token");
      if (refreshToken) {
        await apiRequest("/auth/logout", {
          method: "POST",
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
      }
    } catch (err) {
      console.warn("Logout request failed, logging out locally:", err);
    } finally {
      localStorage.removeItem("logistika_access_token");
      localStorage.removeItem("logistika_refresh_token");
      localStorage.removeItem("logistika_user_role");
      setUser(null);
    }
  };

  const resetPhone = async (phone_number: string) => {
    const res = await apiRequest<{ detail: string; access_token: string }>("/auth/reset-phone", {
      method: "POST",
      body: JSON.stringify({ phone_number: formatPhoneForApi(phone_number) }),
      skipAuth: true,
    });
    // Set temp token to perform code verification
    localStorage.setItem("logistika_access_token", res.access_token);
    return res;
  };

  const verifyResetCode = async (code: string) => {
    return await apiRequest<{ detail: string }>("/auth/verify-reset-code", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
  };

  const resetPassword = async (password: string, confirm: string) => {
    const res = await apiRequest<{ detail: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ new_password: password, confirm_password: confirm }),
    });
    // Clear temp token
    localStorage.removeItem("logistika_access_token");
    return res;
  };

  const updateProfile = async (data: UserUpdateData) => {
    const updated = await apiRequest<User>("/auth/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
    setUser(updated);
    return updated;
  };

  const refreshMe = async () => {
    const updated = await apiRequest<User>("/auth/me");
    setUser(updated);
    return updated;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        login,
        logout,
        resetPhone,
        verifyResetCode,
        resetPassword,
        updateProfile,
        refreshMe,
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
