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

export function isAuthority(principal: Principal | undefined): boolean {
  return Boolean(principal && !isAdmin(principal) && principal.roles.includes(STAFF_ROLES.districtAdmin));
}

export function canSeeResidentData(principal: Principal | undefined): boolean {
  return Boolean(principal && !isAuthority(principal));
}

export function canBrowseOrganizations(principal: Principal | undefined): boolean {
  return Boolean(
    principal?.roles.some((role) => role === STAFF_ROLES.admin || role === STAFF_ROLES.districtAdmin),
  );
}

const ROLE_PRIORITY: readonly string[] = [STAFF_ROLES.admin, STAFF_ROLES.districtAdmin, STAFF_ROLES.housingWorker];

export function primaryRole(principal: Principal | undefined): string | null {
  if (!principal) return null;
  return ROLE_PRIORITY.find((role) => principal.roles.includes(role)) ?? null;
}

export function roleLabel(role: string): string {
  switch (role) {
    case STAFF_ROLES.admin:
      return 'Администратор платформы';
    case STAFF_ROLES.districtAdmin:
      return 'Сотрудник органа власти';
    case STAFF_ROLES.housingWorker:
      return 'Сотрудник управляющей компании';
    default:
      return role;
  }
}
