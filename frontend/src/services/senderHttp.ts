import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { normalizeApiBaseUrl } from "../api";
import { getTelegramInitData } from "../auth/telegram";

function getBaseUrl(): string {
  const savedUrl = localStorage.getItem("logistika_backend_url");
  if (savedUrl) return normalizeApiBaseUrl(savedUrl);

  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return "http://logistic.org.uz:8000/api";
  }
  return `${window.location.origin}/api`;
}

let activeRefreshPromise: Promise<string> | null = null;

export const senderHttp = axios.create({
  headers: { "Content-Type": "application/json" },
});

senderHttp.interceptors.request.use((config) => {
  config.baseURL = getBaseUrl();

  const token = localStorage.getItem("logistika_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  const initData = getTelegramInitData();
  if (initData) {
    config.headers["X-Telegram-Init-Data"] = initData;
  }

  return config;
});

senderHttp.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string; message?: string }>) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      const refreshToken = localStorage.getItem("logistika_refresh_token");

      if (refreshToken) {
        try {
          let newAccessToken = "";

          if (activeRefreshPromise) {
            newAccessToken = await activeRefreshPromise;
          } else {
            activeRefreshPromise = (async () => {
              const baseUrl = getBaseUrl();
              const { data } = await axios.post(`${baseUrl}/auth/refresh`, {
                refresh_token: refreshToken,
              });
              const { applyRefreshedTokens } = await import("./authApi");
              applyRefreshedTokens(data);
              return data.access_token as string;
            })();

            newAccessToken = await activeRefreshPromise;
            activeRefreshPromise = null;
          }

          original.headers.Authorization = `Bearer ${newAccessToken}`;
          return senderHttp(original);
        } catch {
          activeRefreshPromise = null;
          localStorage.removeItem("logistika_access_token");
          localStorage.removeItem("logistika_refresh_token");
          localStorage.removeItem("logistika_user_role");
          window.dispatchEvent(new Event("auth_session_expired"));
          return Promise.reject(new Error("Sessiya muddati tugadi. Tizimga qayta kiring."));
        }
      }
    }

    const body = error.response?.data;
    const message =
      (typeof body?.detail === "string" ? body.detail : null) ||
      body?.message ||
      error.message ||
      "Xatolik yuz berdi";

    return Promise.reject(new Error(message));
  }
);
