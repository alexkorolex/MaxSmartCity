import { http } from '@/shared/api';

import type { Incident } from '../model/types';

interface ListParams {
  city?: string;
  limit?: number;
  offset?: number;
}

export function fetchIncidents(params: ListParams = {}): Promise<Incident[]> {
  return http.get<Incident[]>('/incidents/', {
    query: {
      city: params.city,
      limit: params.limit ?? 100,
      offset: params.offset,
    },
  });
}

export function fetchIncident(incidentId: string): Promise<Incident> {
  return http.get<Incident>(`/incidents/${incidentId}`);
}
