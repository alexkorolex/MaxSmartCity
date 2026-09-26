import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  fetchIncident,
  fetchMyIncidentReport,
  fetchMyHouseIncidents,
  sendResolutionFeedback,
} from '../api/incidents';

export const incidentQueryKey = (incidentId: string) => ['incidents', incidentId] as const;
export const myHouseIncidentsQueryKey = ['incidents', 'my-house'] as const;
export const myIncidentReportQueryKey = (incidentId: string) => ['incidents', incidentId, 'my-report'] as const;

export function useIncident(incidentId: string) {
  return useQuery({ queryKey: incidentQueryKey(incidentId), queryFn: () => fetchIncident(incidentId) });
}

export function useMyHouseIncidents() {
  return useQuery({ queryKey: myHouseIncidentsQueryKey, queryFn: fetchMyHouseIncidents });
}

export function useMyIncidentReport(incidentId: string) {
  return useQuery({
    queryKey: myIncidentReportQueryKey(incidentId),
    queryFn: () => fetchMyIncidentReport(incidentId),
    enabled: Boolean(incidentId),
  });
}

export function useResolutionFeedback(incidentId: string, reportId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ feedback, comment }: { feedback: 'CONFIRMED' | 'PROBLEM_CONTINUES'; comment: string | null }) => {
      if (!reportId) throw new Error('Обращение не найдено');
      return sendResolutionFeedback(incidentId, reportId, feedback, comment);
    },
    onSuccess: () => {
      for (const key of [['incidents'], ['reports'], ['notifications']]) {
        void queryClient.invalidateQueries({ queryKey: key });
      }
    },
  });
}
