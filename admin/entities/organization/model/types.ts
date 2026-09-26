export type OrganizationType =
  | 'ADMINISTRATION'
  | 'POWER_GRID'
  | 'WATER_UTILITY'
  | 'EMERGENCY'
  | 'MANAGEMENT_COMPANY'
  | 'HOA';

export type HousingOrganizationType = Extract<OrganizationType, 'MANAGEMENT_COMPANY' | 'HOA'>;

export type AuthorityKind =
  | 'CITY_ADMINISTRATION'
  | 'PREFECTURE'
  | 'DISTRICT_ADMINISTRATION'
  | 'DISTRICT_UPRAVA'
  | 'INTRACITY_MUNICIPALITY'
  | 'LOCAL_ADMINISTRATION';

export interface Organization {
  id: string;
  code: string;
  name: string;
  type: OrganizationType;
  enabled: boolean;
  city: string | null;
  inn: string | null;
  ogrn: string | null;
  license_number: string | null;
  in_reserve_registry: boolean;
  authority_kind: AuthorityKind | null;
  territory_id: string | null;
}

export interface AuthorityRegistrationPayload {
  name: string;
  authority_kind: AuthorityKind;
  territory_id: string;
  inn?: string | null;
  ogrn?: string | null;
  employee: StaffAccountPayload;
}

export interface StaffAccountPayload {
  login: string;
  password: string;
  display_name: string;
  email?: string | null;
}

export interface OrganizationRegistrationPayload {
  code: string;
  name: string;
  type: HousingOrganizationType;
  inn: string;
  ogrn: string;
  city?: string | null;
  license_number?: string | null;
  in_reserve_registry: boolean;
  employee: StaffAccountPayload;
}

export interface OrganizationMember {
  id: string;
  organization_id: string;
  user_id: string;
  login: string;
  display_name: string;
  email: string | null;
  has_max_account: boolean;
  department_id: string | null;
  department_name: string | null;
  role_code: string;
  is_active: boolean;
  created_at: string;
}

/** Whether the new employee was e-mailed their login and temporary password. */
export interface CredentialsEmailResult {
  recipient: string | null;
  sent: boolean;
  error: string | null;
}

export interface OrganizationRegistrationResult {
  organization_id: string;
  employee: OrganizationMember;
  credentials_email: CredentialsEmailResult;
}

export interface StaffAccountCreatedResult {
  member: OrganizationMember;
  credentials_email: CredentialsEmailResult;
}

export const ORGANIZATION_TYPE_LABELS: Record<OrganizationType, string> = {
  ADMINISTRATION: 'Орган власти',
  POWER_GRID: 'Энергосети',
  WATER_UTILITY: 'Водоканал',
  EMERGENCY: 'Аварийная служба',
  MANAGEMENT_COMPANY: 'Управляющая компания',
  HOA: 'ТСЖ',
};

export const HOUSING_ORGANIZATION_TYPES: HousingOrganizationType[] = ['MANAGEMENT_COMPANY', 'HOA'];

export const AUTHORITY_KIND_LABELS: Record<AuthorityKind, string> = {
  CITY_ADMINISTRATION: 'Администрация города',
  PREFECTURE: 'Префектура округа',
  DISTRICT_ADMINISTRATION: 'Администрация района',
  DISTRICT_UPRAVA: 'Управа района',
  INTRACITY_MUNICIPALITY: 'Внутригородское МО',
  LOCAL_ADMINISTRATION: 'Местная администрация',
};

export const AUTHORITY_KINDS = Object.keys(AUTHORITY_KIND_LABELS) as AuthorityKind[];
