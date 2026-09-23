import { http } from '@/shared/api';

import type { ResidentProfile, ResidentSelfUpdate } from '../model/types';

export function fetchMyProfile(): Promise<ResidentProfile> {
  return http.get<ResidentProfile>('/identity/me/resident');
}

export function updateMyProfile(patch: ResidentSelfUpdate): Promise<ResidentProfile> {
  return http.patch<ResidentProfile>('/identity/me/resident', patch);
}
