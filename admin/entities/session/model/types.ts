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

/**
 * The platform admin and the district administration (Управа) browse every organization;
 * a housing worker (жилищник) only ever sees their own - mirrors the backend's
 * `_ORGANIZATION_DIRECTORY_ROLES` / `_HOUSE_MANAGEMENT_AUTHORITY_ROLES`.
 */
export function canBrowseOrganizations(principal: Principal | undefined): boolean {
  return Boolean(
    principal?.roles.some((role) => role === STAFF_ROLES.admin || role === STAFF_ROLES.districtAdmin),
  );
}

const ROLE_PRIORITY: readonly string[] = [STAFF_ROLES.admin, STAFF_ROLES.districtAdmin, STAFF_ROLES.housingWorker];

/**
 * The caller's staff role, highest first. The token also carries Keycloak's technical
 * roles (`default-roles-<realm>`, `offline_access`, ...) - those are never shown.
 */
export function primaryRole(principal: Principal | undefined): string | null {
  if (!principal) return null;
  return ROLE_PRIORITY.find((role) => principal.roles.includes(role)) ?? null;
}

export function roleLabel(role: string): string {
  switch (role) {
    case STAFF_ROLES.admin:
      return 'Администратор платформы';
    case STAFF_ROLES.districtAdmin:
      return 'Сотрудник управы';
    case STAFF_ROLES.housingWorker:
      return 'Сотрудник управляющей компании';
    default:
      return role;
  }
}
