export type ReportStatus =
  | 'RECEIVED'
  | 'PROCESSING'
  | 'READY_FOR_TRIAGE'
  | 'LINKED'
  | 'NEEDS_CLARIFICATION'
  | 'REJECTED'
  | 'WITHDRAWN';

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

export interface ReportAttachment {
  id: string;
  original_name: string | null;
  mime_type: string;
  size_bytes: number;
  created_at: string;
  download_url: string;
}
