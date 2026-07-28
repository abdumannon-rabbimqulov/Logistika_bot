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

// Parolni tiklash oqimi (3 qadam). Barcha so'rovlar `/auth/login` bilan bir xil
// standartda: JSON body + `Content-Type: application/json` (client.ts `request`
// har bir so'rovga shu sarlavhani qo'yadi va body'ni JSON.stringify qiladi).
// Payload maydonlari backend pydantic sxemalari bilan bir xil (users/schemas.py).

/** users/schemas.py `ResetPhoneSchema` */
interface ResetPhonePayload {
  phone_number: string;
}

/** users/schemas.py `VerifyResetCodeSchema` */
interface VerifyResetCodePayload {
  phone_number: string;
  code: string;
}

/** users/schemas.py `ResetPasswordSchema` */
interface ResetPasswordPayload {
  reset_token: string;
  new_password: string;
  confirm_password: string;
}

/** Parol hali yo'q/unutilgan bo'lsa — Telegramga kod yuboradi (3 qadamli tiklash oqimi). */
export function requestPasswordResetCode(phoneNumber: string): Promise<{ detail: string }> {
  const payload: ResetPhonePayload = { phone_number: phoneNumber };
  return api.post('/auth/reset-phone', payload, true);
}

export function verifyPasswordResetCode(phoneNumber: string, code: string): Promise<{ detail: string; reset_token: string }> {
  const payload: VerifyResetCodePayload = { phone_number: phoneNumber, code };
  return api.post('/auth/verify-reset-code', payload, true);
}

export function setNewPassword(resetToken: string, newPassword: string, confirmPassword: string): Promise<{ detail: string }> {
  const payload: ResetPasswordPayload = {
    reset_token: resetToken,
    new_password: newPassword,
    confirm_password: confirmPassword,
  };
  return api.post('/auth/reset-password', payload, true);
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
