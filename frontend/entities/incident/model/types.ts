export type IncidentStatus =
  | 'NEW'
  | 'TRIAGE'
  | 'CONFIRMED'
  | 'ASSIGNED'
  | 'IN_PROGRESS'
  | 'RESOLVED'
  | 'AWAITING_CONFIRMATION'
  | 'CLOSED'
  | 'REJECTED'
  | 'CANCELLED'
  | 'MERGED'
  | 'RESOLUTION_DISPUTED'
  | 'REOPENED';

export type IncidentPriority = 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';

export interface Incident {
  id: string;
  title: string;
  description: string | null;
  category_id: string;
  status: IncidentStatus;
  priority: IncidentPriority;
  first_report_at: string | null;
  last_report_at: string | null;
  expected_resolution_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  version: number;
}

export interface ResidentIncidentReport {
  report_id: string;
  has_open_dispute: boolean;
}

export interface ResolutionFeedbackResult {
  incident_id: string;
  report_id: string;
  incident_status: IncidentStatus;
  feedback: 'CONFIRMED' | 'PROBLEM_CONTINUES';
}
