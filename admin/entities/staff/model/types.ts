export interface StaffMember {
  id: string;
  login: string;
  display_name: string;
  email: string | null;
  is_active: boolean;
  organization_id: string | null;
  organization_name: string | null;
  organization_city: string | null;
  department_id: string | null;
  department_name: string | null;
  role_code: string | null;
}

export interface StaffDirectoryEntry {
  member_id: string;
  display_name: string;
  role_code: string;
  organization_id: string;
  organization_name: string;
}
