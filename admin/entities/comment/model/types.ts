export type CommentVisibility = 'INTERNAL' | 'PUBLIC';

export interface IncidentComment {
  id: string;
  incident_id: string;
  assignment_id: string | null;
  work_item_id: string | null;
  author_user_id: string;
  author_display_name: string;
  visibility: CommentVisibility;
  text: string;
  created_at: string;
}

export interface IncidentCommentCreatePayload {
  incident_id: string;
  text: string;
  visibility?: CommentVisibility;
  work_item_id?: string | null;
  assignment_id?: string | null;
}
