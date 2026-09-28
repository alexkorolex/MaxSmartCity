import { http } from '@/shared/api';

import type { Principal } from '../model/types';

export interface StaffTokens {
  token: string;
  refresh_token: string | null;
  expires_in: number | null;
  refresh_expires_in: number | null;
}

export function staffLogin(username: string, password: string): Promise<StaffTokens> {
  return http.post<StaffTokens>('/auth/staff/login', { username, password }, { skipAuthRefresh: true });
}

export function staffInitialPassword(username: string, password: string, newPassword: string): Promise<StaffTokens> {
  return http.post<StaffTokens>(
    '/auth/staff/initial-password',
    { username, password, new_password: newPassword },
    { skipAuthRefresh: true },
  );
}

export function staffRefresh(): Promise<StaffTokens> {
  return http.post<StaffTokens>('/auth/staff/refresh', undefined, { skipAuthRefresh: true });
}

export function staffLogout(): Promise<void> {
  return http.post<void>('/auth/staff/logout', undefined, { skipAuthRefresh: true });
}

export function fetchMe(): Promise<Principal> {
  return http.get<Principal>('/identity/me/');
}

export function linkMaxAccount(maxUserId: number): Promise<{ operator_id: string; max_user_id: number }> {
  return http.post('/auth/staff/max-id', { max_user_id: maxUserId });
}

export interface StaffProfile {
  id: string;
  login: string;
  display_name: string;
  email: string | null;
  max_user_id: number | null;
  organization_name: string | null;
  department_name: string | null;
  role_code: string | null;
}

export function fetchProfile(): Promise<StaffProfile> {
  return http.get<StaffProfile>('/auth/staff/profile');
}

export function updateProfile(payload: { display_name: string; email: string | null }): Promise<StaffProfile> {
  return http.patch<StaffProfile>('/auth/staff/profile', payload);
}

export function changePassword(payload: { current_password: string; new_password: string }): Promise<void> {
  return http.post<void>('/auth/staff/password', payload);
}

export function unlinkMaxAccount(): Promise<void> {
  return http.delete<void>('/auth/staff/max-id');
}
