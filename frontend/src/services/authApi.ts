import { apiRequest } from "../api";
import type { LoginPayload, LoginResponse } from "../types/auth";
import type { User, UserUpdateData } from "../types";
import { loadAuthSession, persistAuthSession } from "../auth/session";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export async function loginApi(payload: LoginPayload): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true,
  });
}

export async function refreshTokensApi(refreshToken: string): Promise<TokenPair> {
  return apiRequest<TokenPair>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
    skipAuth: true,
  });
}

export async function fetchMeApi(): Promise<User> {
  return apiRequest<User>("/auth/me");
}

export async function updateMeApi(data: UserUpdateData): Promise<User> {
  return apiRequest<User>("/auth/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function changePasswordApi(old_password: string, new_password: string): Promise<{ detail: string }> {
  return apiRequest("/auth/me/password", {
    method: "PATCH",
    body: JSON.stringify({ old_password, new_password }),
  });
}

export async function deactivateMeApi(): Promise<{ detail: string }> {
  return apiRequest("/auth/me", { method: "DELETE" });
}

export async function logoutApi(refreshToken: string): Promise<void> {
  await apiRequest("/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export async function resetPhoneApi(phone_number: string): Promise<{ detail: string; access_token: string }> {
  return apiRequest("/auth/reset-phone", {
    method: "POST",
    body: JSON.stringify({ phone_number }),
    skipAuth: true,
  });
}

export async function verifyResetCodeApi(code: string): Promise<{ detail: string }> {
  return apiRequest("/auth/verify-reset-code", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export async function resetPasswordApi(
  new_password: string,
  confirm_password: string
): Promise<{ detail: string }> {
  return apiRequest("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ new_password, confirm_password }),
  });
}

/** Refresh javobidan keyin sessiyani yangilash (api interceptor uchun). */
export function applyRefreshedTokens(tokens: TokenPair): void {
  const prev = loadAuthSession();
  if (!prev) return;
  persistAuthSession({
    ...prev,
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token,
  });
}
