export type OrganizationType = 'ADMINISTRATION' | 'POWER_GRID' | 'WATER_UTILITY' | 'EMERGENCY';

export interface Organization {
  id: string;
  code: string;
  name: string;
  type: OrganizationType;
  enabled: boolean;
  city: string | null;
}

export const ORGANIZATION_TYPE_LABELS: Record<OrganizationType, string> = {
  ADMINISTRATION: 'Управа',
  POWER_GRID: 'Энергосети',
  WATER_UTILITY: 'Водоканал',
  EMERGENCY: 'Аварийная служба',
};
