import { http } from '@/shared/api';

import type { Organization } from '../model/types';

export function fetchOrganizations(): Promise<Organization[]> {
  // Small dataset (a handful of organizations) - fetched whole and filtered by city
  // client-side (see model/queries.ts), same as the resident app does for its house list.
  return http.get<Organization[]>('/identity/organizations/', { query: { limit: 100 } });
}

export function fetchOrganization(organizationId: string): Promise<Organization> {
  return http.get<Organization>(`/identity/organizations/${organizationId}`);
}
