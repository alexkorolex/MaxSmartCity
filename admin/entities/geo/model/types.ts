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
