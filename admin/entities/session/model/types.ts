export interface Principal {
  actor_type: string;
  actor_id: string;
  roles: string[];
  organization_id: string | null;
  department_id: string | null;
}

export const STAFF_ROLES = {
  admin: 'admin',
  districtAdmin: 'district_admin',
  housingWorker: 'housing_worker',
} as const;

export function isAdmin(principal: Principal | undefined): boolean {
  return Boolean(principal?.roles.includes(STAFF_ROLES.admin));
}

export function roleLabel(role: string): string {
  switch (role) {
    case STAFF_ROLES.admin:
      return 'Администратор';
    case STAFF_ROLES.districtAdmin:
      return 'Управа';
    case STAFF_ROLES.housingWorker:
      return 'Жилищник';
    default:
      return role;
  }
}
