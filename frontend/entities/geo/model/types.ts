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
  /** `DEMO` data must never be presented to a resident as a real fact. */
  data_kind: 'REAL' | 'DEMO' | string;
  retrieved_at: string;
}

/** The house's management company as published in open sources, with its contacts. */
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
  /** Connected to Smart City - residents' requests reach it directly. */
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

/**
 * Open registries (GIS ЖКХ) tag every manager as `MANAGING_COMPANY`, so an HOA is told
 * apart by the house's management method or by its name.
 */
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
