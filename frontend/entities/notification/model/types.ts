export type NotificationType =
  | 'REPORT_STATUS_CHANGED'
  | 'INCIDENT_STATUS_CHANGED'
  | 'RESOLUTION_REQUESTED'
  | 'NEWS'
  | 'GENERIC';

export interface AppNotification {
  id: string;
  resident_id: string;
  type: NotificationType;
  title: string;
  body: string;
  incident_id: string | null;
  report_id: string | null;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
}
