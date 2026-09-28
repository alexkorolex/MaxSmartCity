export type ReportStatus =
  | 'RECEIVED'
  | 'PROCESSING'
  | 'READY_FOR_TRIAGE'
  | 'LINKED'
  | 'NEEDS_CLARIFICATION'
  | 'REJECTED'
  | 'WITHDRAWN'
  | 'CLOSED';

export type Priority = 'LOW' | 'NORMAL' | 'HIGH' | 'CRITICAL';

export interface ProblemCategory {
  id: string;
  code: string;
  name: string;
  is_critical: boolean;
  enabled: boolean;
}

export interface Report {
  id: string;
  resident_id: string | null;
  text: string | null;
  status: ReportStatus;
  category_id: string | null;
  urgency: Priority;
  house_id: string | null;
  problem_continues: boolean | null;
  occurred_at: string | null;
  received_at: string;
}

export interface ReportCreatePayload {
  source_external_id: string;
  request_id: string;
  house_id: string;
  category_code: string;
  text: string;
  urgency: Priority;
  problem_continues: boolean;
}

export interface GroupingResult {
  report_id: string;
  outcome: 'CREATED' | 'ATTACHED' | 'NEEDS_CLARIFICATION';
  incident_id: string | null;
  score: number | null;
  candidate_incident_ids: string[];
  candidate_incidents: {
    incident_id: string;
    title: string;
    description: string | null;
    score: number | null;
    headline: string | null;
    category_name: string | null;
    reports_count: number;
    first_report_at: string | null;
    last_report_at: string | null;
  }[];
  reason_codes: string[];
  policy_version: string;
  scorer_version: string;
}

export interface ReportCreateResult {
  report_id: string;
  grouping: GroupingResult;
}

export type GroupingDecision =
  | { mode: 'CONFIRM_INCIDENT'; confirmed_incident_id: string }
  | { mode: 'FORCE_NEW' };

export interface ReportAttachment {
  id: string;
  original_name: string | null;
  mime_type: string;
  size_bytes: number;
  created_at: string;
  download_url: string;
}

export interface CloseReportResult {
  report_id: string;
  report_status: ReportStatus;
  incident_id: string | null;
  incident_status: string | null;
}

export const FINAL_REPORT_STATUSES: ReadonlySet<ReportStatus> = new Set<ReportStatus>([
  'CLOSED',
  'REJECTED',
  'WITHDRAWN',
]);

export interface ChatMessage {
  id: string;
  author_type: 'RESIDENT' | 'OPERATOR';
  author_name: string;
  organization_name: string | null;
  text: string;
  created_at: string;
  read_at: string | null;
  is_mine: boolean;
}

export interface ReportChatThread {
  report_id: string;
  report_text: string | null;
  counterparts: string[];
  can_write: boolean;
  messages: ChatMessage[];
}
