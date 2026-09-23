import { useQuery } from '@tanstack/react-query';

import { fetchIncident, fetchIncidents } from '../api/incidents';

export const incidentsQueryKey = (city?: string) => ['incidents', city ?? ''] as const;
export const incidentQueryKey = (incidentId: string) => ['incidents', 'member', incidentId] as const;

export function useIncidents(city?: string) {
  return useQuery({
    queryKey: incidentsQueryKey(city),
    queryFn: () => fetchIncidents({ city }),
  });
}

export function useIncident(incidentId: string) {
  return useQuery({
    queryKey: incidentQueryKey(incidentId),
    queryFn: () => fetchIncident(incidentId),
    enabled: Boolean(incidentId),
  });
}
