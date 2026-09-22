import { http } from '@/shared/api';

import type { Incident, ResolutionDispute } from '../model/types';

export function fetchIncident(incidentId: string): Promise<Incident> {
  return http.get<Incident>(`/incidents/${incidentId}`);
}

export function fetchMyHouseIncidents(): Promise<Incident[]> {
  return http.get<Incident[]>('/incidents/my-house');
}

export function confirmResolution(incidentId: string): Promise<Incident> {
  return http.post<Incident>(`/incidents/${incidentId}/confirm-resolution`);
}

export function disputeResolution(incidentId: string, comment: string): Promise<ResolutionDispute> {
  return http.post<ResolutionDispute>(`/incidents/${incidentId}/dispute-resolution`, { comment });
}

export function fetchIncidentDisputes(incidentId: string): Promise<ResolutionDispute[]> {
  return http.get<ResolutionDispute[]>(`/incidents/${incidentId}/disputes`);
}
