import { http } from '@/shared/api';

import type { Resident } from '../model/types';

interface ListParams {
  city?: string;
  limit?: number;
  offset?: number;
}

export function fetchResidents(params: ListParams = {}): Promise<Resident[]> {
  return http.get<Resident[]>('/identity/residents/', {
    query: {
      city: params.city,
      limit: params.limit ?? 100,
      offset: params.offset,
    },
  });
}

export function fetchResident(residentId: string): Promise<Resident> {
  return http.get<Resident>(`/identity/residents/${residentId}`);
}
