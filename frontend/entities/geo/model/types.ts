export interface House {
  house_id: string;
  city: string | null;
  street: string | null;
  house_number: string | null;
  formatted: string;
  managed_by_organization_id: string | null;
  managed_by_organization_name: string | null;
}

export interface HouseDataSource {
  code: string;
  url: string | null;
  data_kind: 'REAL' | 'DEMO' | string;
  retrieved_at: string;
}

export interface HouseManagingOrganization {
  name: string;
  type: string;
  inn: string | null;
  ogrn: string | null;
  phones: string[];
  email: string | null;
  website: string | null;
  basis: string | null;
  period_from: string | null;
  is_platform_manager: boolean;
  sources: HouseDataSource[];
}

export interface HousePlatformManager {
  organization_id: string;
  name: string;
  type: string;
  inn: string | null;
  ogrn: string | null;
  effective_from: string | null;
}

export interface HouseInfo {
  house: House;
  management_method: string | null;
  official_status: string | null;
  platform_manager: HousePlatformManager | null;
  managing_organizations: HouseManagingOrganization[];
}

export const MANAGING_ORGANIZATION_TYPE_LABELS: Record<string, string> = {
  MANAGING_COMPANY: 'Управляющая компания',
  MANAGEMENT_COMPANY: 'Управляющая компания',
  HOA: 'ТСЖ',
};

export function managingOrganizationLabel(
  organization: Pick<HouseManagingOrganization, 'type' | 'name'>,
  managementMethod: string | null,
): string {
  const isHoa =
    organization.type === 'HOA' ||
    managementMethod === 'ТСЖ' ||
    /^(ТСЖ|ТОВАРИЩЕСТВО СОБСТВЕННИКОВ)/.test(organization.name.trim().toUpperCase());
  if (isHoa) return 'ТСЖ';
  return MANAGING_ORGANIZATION_TYPE_LABELS[organization.type] ?? 'Управляющая организация';
}
