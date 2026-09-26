export interface CorrespondenceContact {
  organization_id: string | null;
  name: string;
  kind: string;
}

export interface ConversationSummary {
  id: string;
  subject: string;
  counterpart_name: string;
  last_message_text: string | null;
  last_message_at: string;
  unread_count: number;
}

export interface ConversationMessage {
  id: string;
  text: string;
  created_at: string;
  author_name: string;
  organization_name: string;
  is_mine: boolean;
}

export interface ConversationThread {
  id: string;
  subject: string;
  counterpart_name: string;
  counterpart_read_at: string | null;
  messages: ConversationMessage[];
}

export interface StartConversationPayload {
  organization_id: string | null;
  subject: string;
  text: string;
}
