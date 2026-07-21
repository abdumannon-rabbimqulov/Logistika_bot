import { api } from './client';
import type { LoginResponse, UserProfile, UserRole } from '../types/api';

export function loginWithInitData(initData: string): Promise<LoginResponse> {
  return api.post<LoginResponse>('/auth/login', { init_data: initData }, true);
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
