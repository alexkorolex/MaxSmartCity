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

export interface ChatThread {
  report_id: string;
  report_text: string | null;
  counterparts: string[];
  can_write: boolean;
  messages: ChatMessage[];
}

export interface ChatConversation {
  report_id: string;
  report_text: string | null;
  address: string | null;
  resident_name: string | null;
  last_message_text: string;
  last_message_at: string;
  last_message_from_resident: boolean;
  unread_count: number;
}
