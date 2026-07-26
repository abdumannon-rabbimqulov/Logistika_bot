import { api } from './client';
import type { LoginResponse, UserProfile, UserRole } from '../types/api';

export function loginWithInitData(initData: string): Promise<LoginResponse> {
  return api.post<LoginResponse>('/auth/login', { init_data: initData }, true);
}

/** Telegram tashqarisida (oddiy brauzer/local manzil) kirish uchun — backendda
 * allaqachon mavjud telefon+parol oqimi (users/router.py `login`). */
export function loginWithPassword(phoneNumber: string, password: string): Promise<LoginResponse> {
  return api.post<LoginResponse>('/auth/login', { phone_number: phoneNumber, password }, true);
}

/** Parol hali yo'q/unutilgan bo'lsa — Telegramga kod yuboradi (3 qadamli tiklash oqimi). */
export function requestPasswordResetCode(phoneNumber: string): Promise<{ detail: string }> {
  return api.post('/auth/reset-phone', { phone_number: phoneNumber }, true);
}

export function verifyPasswordResetCode(phoneNumber: string, code: string): Promise<{ detail: string; reset_token: string }> {
  return api.post('/auth/verify-reset-code', { phone_number: phoneNumber, code }, true);
}

export function setNewPassword(resetToken: string, newPassword: string, confirmPassword: string): Promise<{ detail: string }> {
  return api.post('/auth/reset-password', { reset_token: resetToken, new_password: newPassword, confirm_password: confirmPassword }, true);
}

export function getMe(): Promise<UserProfile> {
  return api.get<UserProfile>('/auth/me');
}

export function updateMe(data: Partial<Pick<UserProfile, 'full_name' | 'phone_number' | 'language'>> & { bio?: string }): Promise<UserProfile> {
  return api.patch<UserProfile>('/auth/me', data);
}

/** GUEST birinchi marta rolini tanlaydi — faqat sender/driver (users/router.py `select_role`). */
export function selectRole(role: Extract<UserRole, 'sender' | 'driver'>): Promise<UserProfile> {
  return api.post<UserProfile>('/auth/select-role', { role });
}

export function logout(): Promise<void> {
  return api.post<void>('/auth/logout');
}
