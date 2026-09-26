import { http } from '@/shared/api';

import type { Incident, ResidentIncidentReport, ResolutionFeedbackResult } from '../model/types';

export function fetchIncident(incidentId: string): Promise<Incident> {
  return http.get<Incident>(`/incidents/${incidentId}`);
}

export function fetchMyHouseIncidents(): Promise<Incident[]> {
  return http.get<Incident[]>('/incidents/my-house');
}

export function fetchMyIncidentReport(incidentId: string): Promise<ResidentIncidentReport> {
  return http.get<ResidentIncidentReport>(`/incidents/${incidentId}/my-report`);
}

export function sendResolutionFeedback(
  incidentId: string,
  reportId: string,
  feedback: 'CONFIRMED' | 'PROBLEM_CONTINUES',
  comment: string | null,
): Promise<ResolutionFeedbackResult> {
  return http.post<ResolutionFeedbackResult>(`/incidents/${incidentId}/resolution-feedback`, {
    report_id: reportId,
    feedback,
    comment,
  });
}
