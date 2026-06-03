import type { AuthSession, AuthStatus, LoginResponse, UserRole } from "../types/auth";

const KEYS = {
  access: "logistika_access_token",
  refresh: "logistika_refresh_token",
  role: "logistika_user_role",
  userId: "logistika_user_id",
  status: "logistika_auth_status",
} as const;

function normalizeStatus(status?: string): AuthStatus {
  return status === "need_driver_profile" ? "need_driver_profile" : "active";
}

export function sessionFromLoginResponse(data: LoginResponse): AuthSession {
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    role: data.role as UserRole,
    userId: data.user_id,
    status: normalizeStatus(data.status),
    message: data.message,
  };
}

export function persistAuthSession(session: AuthSession): void {
  localStorage.setItem(KEYS.access, session.accessToken);
  localStorage.setItem(KEYS.refresh, session.refreshToken);
  localStorage.setItem(KEYS.role, session.role);
  localStorage.setItem(KEYS.userId, String(session.userId));
  localStorage.setItem(KEYS.status, session.status);
}

export function loadAuthSession(): AuthSession | null {
  const accessToken = localStorage.getItem(KEYS.access);
  const refreshToken = localStorage.getItem(KEYS.refresh);
  const role = localStorage.getItem(KEYS.role) as UserRole | null;
  const userIdRaw = localStorage.getItem(KEYS.userId);

  if (!accessToken || !refreshToken || !role || !userIdRaw) {
    return null;
  }

  return {
    accessToken,
    refreshToken,
    role,
    userId: Number(userIdRaw),
    status: normalizeStatus(localStorage.getItem(KEYS.status) || undefined),
  };
}

export function clearAuthSession(): void {
  localStorage.removeItem(KEYS.access);
  localStorage.removeItem(KEYS.refresh);
  localStorage.removeItem(KEYS.role);
  localStorage.removeItem(KEYS.userId);
  localStorage.removeItem(KEYS.status);
}

export function markProfileComplete(): void {
  localStorage.setItem(KEYS.status, "active");
}
