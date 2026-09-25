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

/** New access token for the still valid (24 h) session - no password. */
export function staffRefresh(refreshToken: string): Promise<StaffTokens> {
  return http.post<StaffTokens>('/auth/staff/refresh', { refresh_token: refreshToken }, { skipAuthRefresh: true });
}

/** Ends the session server-side, so the refresh token stops working too. */
export function staffLogout(refreshToken: string): Promise<void> {
  return http.post<void>('/auth/staff/logout', { refresh_token: refreshToken }, { skipAuthRefresh: true });
}

export function fetchMe(): Promise<Principal> {
  return http.get<Principal>('/identity/me/');
}

/** Link the signed-in staff member's own MAX account - for personal request notifications. */
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
