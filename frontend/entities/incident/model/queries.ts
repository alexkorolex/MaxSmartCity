import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  confirmResolution,
  disputeResolution,
  fetchIncident,
  fetchIncidentDisputes,
  fetchMyHouseIncidents,
} from '../api/incidents';

export const incidentQueryKey = (incidentId: string) => ['incidents', incidentId] as const;
export const myHouseIncidentsQueryKey = ['incidents', 'my-house'] as const;
export const incidentDisputesQueryKey = (incidentId: string) => ['incidents', incidentId, 'disputes'] as const;

export function useIncident(incidentId: string) {
  return useQuery({ queryKey: incidentQueryKey(incidentId), queryFn: () => fetchIncident(incidentId) });
}

export function useMyHouseIncidents() {
  return useQuery({ queryKey: myHouseIncidentsQueryKey, queryFn: fetchMyHouseIncidents });
}

export function useIncidentDisputes(incidentId: string) {
  return useQuery({
    queryKey: incidentDisputesQueryKey(incidentId),
    queryFn: () => fetchIncidentDisputes(incidentId),
  });
}

export function useConfirmResolution(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => confirmResolution(incidentId),
    onSuccess: (incident) => {
      queryClient.setQueryData(incidentQueryKey(incidentId), incident);
    },
  });
}

export function useDisputeResolution(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (comment: string) => disputeResolution(incidentId, comment),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: incidentQueryKey(incidentId) });
      void queryClient.invalidateQueries({ queryKey: incidentDisputesQueryKey(incidentId) });
    },
  });
}
