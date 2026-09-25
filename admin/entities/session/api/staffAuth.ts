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
