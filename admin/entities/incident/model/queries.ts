import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { completeIncident, fetchIncident, fetchIncidentReports, fetchIncidents } from '../api/incidents';

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

export function useCompleteIncident(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (comment: string | null) => completeIncident(incidentId, comment),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['incidents'] });
      void queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });
}

export function useIncidentReports(incidentId: string) {
  return useQuery({
    queryKey: ['incidents', 'member', incidentId, 'reports'],
    queryFn: () => fetchIncidentReports(incidentId),
    enabled: Boolean(incidentId),
  });
}
