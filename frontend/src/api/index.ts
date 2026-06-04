// Production-grade Fetch Wrapper with Auto-Refresh Token Interceptor

/** Backend barcha route'lari /api prefiksi ostida (Postman: .../api/auth/login). */
export function normalizeApiBaseUrl(url: string): string {
  const trimmed = url.trim().replace(/\/+$/, "");
  if (!trimmed) return trimmed;
  return trimmed.endsWith("/api") ? trimmed : `${trimmed}/api`;
}

const getBaseUrl = (): string => {
  const savedUrl = localStorage.getItem("logistika_backend_url");
  if (savedUrl) return normalizeApiBaseUrl(savedUrl);

  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return "http://127.0.0.1:8000/api";
  }
  return `${window.location.origin}/api`;
};

export const API_BASE_URL = getBaseUrl();

/** Backend static fayllar (/static/uploads/...) — API origin bilan to'liq URL. */
export function resolveMediaUrl(url: string | null | undefined): string | undefined {
  if (!url?.trim()) return undefined;
  const trimmed = url.trim();
  if (/^https?:\/\//i.test(trimmed)) return trimmed;

  let path = trimmed;
  if (!path.startsWith("/")) {
    const bare = path.replace(/^static\/uploads\/?/i, "");
    path = `/static/uploads/${bare}`;
  }

  const apiBase = getBaseUrl();
  const origin = apiBase.replace(/\/api\/?$/i, "") || window.location.origin;
  return `${origin}${path}`;
}

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
}

// Global active refresh promise to deduplicate multiple simultaneous refresh calls
let activeRefreshPromise: Promise<string> | null = null;

export async function apiRequest<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const { skipAuth = false, ...init } = options;
  const baseUrl = getBaseUrl();
  const url = `${baseUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  // Build headers
  const headers = new Headers(init.headers || {});
  if (!headers.has("Content-Type") && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  // Attach access token
  if (!skipAuth) {
    const token = localStorage.getItem("logistika_access_token");
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const finalOptions: RequestInit = {
    ...init,
    headers,
  };

  try {
    let response = await fetch(url, finalOptions);

    // Auto Refresh Token Interceptor
    if (response.status === 401 && !skipAuth) {
      const refreshToken = localStorage.getItem("logistika_refresh_token");
      if (refreshToken) {
        try {
          let newAccessToken = "";
          
          if (activeRefreshPromise) {
            // Wait for existing refresh to complete
            newAccessToken = await activeRefreshPromise;
          } else {
            // Initiate refresh
            activeRefreshPromise = (async () => {
              const refreshUrl = `${baseUrl}/auth/refresh`;
              const refreshRes = await fetch(refreshUrl, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh_token: refreshToken }),
              });

              if (!refreshRes.ok) {
                throw new Error("Refresh token expired");
              }

              const data = await refreshRes.json();
              const { applyRefreshedTokens } = await import("../services/authApi");
              applyRefreshedTokens(data);
              return data.access_token as string;
            })();

            newAccessToken = await activeRefreshPromise;
            activeRefreshPromise = null;
          }

          // Retry the original request with the new token
          headers.set("Authorization", `Bearer ${newAccessToken}`);
          response = await fetch(url, finalOptions);
        } catch (refreshErr) {
          activeRefreshPromise = null;
          // Clear credentials and force redirect
          localStorage.removeItem("logistika_access_token");
          localStorage.removeItem("logistika_refresh_token");
          localStorage.removeItem("logistika_user_role");
          window.dispatchEvent(new Event("auth_session_expired"));
          throw new Error("Sessiya muddati tugadi. Tizimga qayta kiring.");
        }
      }
    }

    if (!response.ok) {
      let errorMessage = "Xatolik yuz berdi";
      try {
        const errBody = await response.json();
        errorMessage = errBody.detail || errBody.message || errorMessage;
      } catch {
        errorMessage = response.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    // Return empty object for 204 No Content
    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error: any) {
    console.error("API Request Error:", error);
    throw error;
  }
}

// Websocket connection URL helper
export const getWebSocketUrl = (endpoint: string): string => {
  const baseUrl = getBaseUrl();
  const wsProto = baseUrl.startsWith("https") ? "wss" : "ws";
  const rawUrl = baseUrl.replace(/^https?:\/\//, "");
  return `${wsProto}://${rawUrl}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;
};
