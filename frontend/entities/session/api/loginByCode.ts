import { http } from '@/shared/api';

interface ResidentTokenResponse {
  token: string;
  resident_id: string;
}

export async function loginByCode(code: string): Promise<ResidentTokenResponse> {
  return http.post<ResidentTokenResponse>('/auth/residents/login', { code });
}
