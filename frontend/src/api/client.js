import axios from "axios";
import {
  clearSessionTokens,
  getAccessToken,
  getRefreshToken,
  isRefreshing,
  persistAccessToken,
  setRefreshToken,
  setRefreshing,
} from "../auth/session";

const api = axios.create({
  baseURL: "/api",
});

api.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

async function refreshTokens() {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("Refresh token topilmadi");
  }

  const response = await axios.post("/api/auth/refresh", {
    refresh_token: refreshToken,
  });

  persistAccessToken(response.data.access_token);
  setRefreshToken(response.data.refresh_token);
  return response.data.access_token;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (!originalRequest || error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!isRefreshing()) {
        setRefreshing(refreshTokens());
      }
      const newAccessToken = await isRefreshing();
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(originalRequest);
    } catch (refreshError) {
      clearSessionTokens();
      return Promise.reject(refreshError);
    } finally {
      setRefreshing(null);
    }
  }
);

export async function loginWithTelegramInitData(initData) {
  const response = await axios.post("/api/auth/telegram/webapp-login", {
    init_data: initData,
  });
  persistAccessToken(response.data.access_token);
  setRefreshToken(response.data.refresh_token);
  return response.data;
}

export async function ensureSession(initData) {
  try {
    if (getRefreshToken()) {
      await refreshTokens();
      return;
    }
  } catch (_) {
    clearSessionTokens();
  }
  await loginWithTelegramInitData(initData);
}

export async function getMyProfile() {
  const response = await api.get("/auth/me");
  return response.data;
}

export default api;
