export interface House {
  house_id: string;
  city: string | null;
  street: string | null;
  house_number: string | null;
  formatted: string;
  managed_by_organization_id: string | null;
  managed_by_organization_name: string | null;
}

export interface HouseManagement {
  id: string;
  house_id: string;
  house_formatted: string;
  organization_id: string;
  organization_name: string;
  organization_type: string;
  organization_inn: string | null;
  is_active: boolean;
  basis: string | null;
  assigned_via_reserve_registry: boolean;
  effective_from: string | null;
  effective_to: string | null;
}

export interface AssignHouseManagementPayload {
  house_id: string;
  organization_id: string;
  basis: string;
  assigned_via_reserve_registry?: boolean;
}

export interface HouseDataSource {
  code: string;
  url: string | null;
  data_kind: string;
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

export interface HouseInfo {
  house: House;
  management_method: string | null;
  official_status: string | null;
  platform_manager: {
    organization_id: string;
    name: string;
    type: string;
    inn: string | null;
    ogrn: string | null;
    effective_from: string | null;
  } | null;
  managing_organizations: HouseManagingOrganization[];
}
