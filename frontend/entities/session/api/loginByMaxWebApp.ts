import { http } from '@/shared/api';

interface ResidentTokenResponse {
  token: string;
  resident_id: string;
}

export async function loginByMaxWebApp(initData: string): Promise<ResidentTokenResponse> {
  return http.post<ResidentTokenResponse>('/auth/residents/max-web-app', { init_data: initData }, { skipReauth: true });
}
