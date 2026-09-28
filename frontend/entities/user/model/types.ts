export interface ResidentProfile {
  id: string;
  max_user_id: number | null;
  max_chat_id: number | null;
  username: string | null;
  display_name: string | null;
  notifications_enabled: boolean;
  bot_status: string;
  last_seen_at: string | null;
  house_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResidentSelfUpdate {
  display_name?: string;
  notifications_enabled?: boolean;
  house_id?: string;
}
