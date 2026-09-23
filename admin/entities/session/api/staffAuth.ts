import { http } from '@/shared/api';

import type { Principal } from '../model/types';

interface StaffLoginResponse {
  token: string;
  refresh_token: string | null;
  expires_in: number | null;
}

export function staffLogin(username: string, password: string): Promise<StaffLoginResponse> {
  return http.post<StaffLoginResponse>('/auth/staff/login', { username, password });
}

export function fetchMe(): Promise<Principal> {
  return http.get<Principal>('/identity/me/');
}
