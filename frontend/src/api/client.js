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

function cleanParams(params) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value !== null && value !== undefined)
  );
}

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

export async function updateMyProfile(data) {
  const response = await api.patch("/auth/me", data);
  return response.data;
}

export async function changeMyPassword(data) {
  const response = await api.patch("/auth/me/password", data);
  return response.data;
}

export async function deleteMyAccount() {
  const response = await api.delete("/auth/me");
  return response.data;
}

export async function listOrders(params = {}) {
  const response = await api.get("/orders", {
    params: cleanParams(params),
  });
  return response.data;
}

export async function createOrder(payload, customerId) {
  const response = await api.post("/orders", payload, {
    params: { customer_id: customerId },
  });
  return response.data;
}

export async function getOrder(orderId) {
  const response = await api.get(`/orders/${orderId}`);
  return response.data;
}

export async function updateOrder(orderId, payload) {
  const response = await api.patch(`/orders/${orderId}`, payload);
  return response.data;
}

export async function updateOrderStatus(orderId, status) {
  const response = await api.patch(`/orders/${orderId}/status`, { status });
  return response.data;
}

export async function assignDriver(orderId, driverId) {
  const response = await api.patch(`/orders/${orderId}/assign-driver`, null, {
    params: { driver_id: driverId },
  });
  return response.data;
}

export async function deleteOrder(orderId) {
  await api.delete(`/orders/${orderId}`);
  return { detail: "Order deleted" };
}

export async function createOffer(orderId, payload, driverId) {
  const response = await api.post(`/orders/${orderId}/offers`, payload, {
    params: { driver_id: driverId },
  });
  return response.data;
}

export async function listOffersForOrder(orderId, status) {
  const response = await api.get(`/orders/${orderId}/offers`, {
    params: cleanParams({ status }),
  });
  return response.data;
}

export async function listOffersByDriver(driverId, params = {}) {
  const response = await api.get(`/drivers/${driverId}/offers`, {
    params: cleanParams(params),
  });
  return response.data;
}

export async function getOffer(offerId) {
  const response = await api.get(`/offers/${offerId}`);
  return response.data;
}

export async function updateOffer(offerId, payload) {
  const response = await api.patch(`/offers/${offerId}`, payload);
  return response.data;
}

export async function updateOfferStatus(offerId, status) {
  const response = await api.patch(`/offers/${offerId}/status`, { status });
  return response.data;
}

export async function acceptOffer(offerId) {
  const response = await api.post(`/offers/${offerId}/accept`);
  return response.data;
}

export async function deleteOffer(offerId) {
  await api.delete(`/offers/${offerId}`);
  return { detail: "Offer deleted" };
}

export async function createTruckType(payload) {
  const response = await api.post("/driver/truck-type-create", payload);
  return response.data;
}

export async function getAllTruckTypes() {
  const response = await api.get("/driver/truck-type-get_all");
  return response.data;
}

export async function getTruckTypeById(pk) {
  const response = await api.get(`/driver/get_truck_type/${pk}`);
  return response.data;
}

export async function updateTruckType(pk, payload) {
  const response = await api.put(`/driver/truck-type-update/${pk}`, payload);
  return response.data;
}

export async function deleteTruckType(pk) {
  await api.delete(`/driver/delete_truck_type/${pk}`);
  return { detail: "Truck type deleted" };
}

export default api;
