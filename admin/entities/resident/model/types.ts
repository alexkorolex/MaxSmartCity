export interface Resident {
  id: string;
  display_name: string | null;
  username: string | null;
  max_user_id: number | null;
  house_id: string | null;
  house_city: string | null;
  house_formatted: string | null;
  reports_count: number;
  created_at: string;
}
