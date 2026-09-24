import { http } from '@/shared/api';

import type {
  Organization,
  OrganizationMember,
  OrganizationRegistrationPayload,
  OrganizationRegistrationResult,
  StaffAccountPayload,
} from '../model/types';

export function fetchOrganizations(): Promise<Organization[]> {
  // Small dataset (a handful of organizations) - fetched whole and filtered by city
  // client-side (see model/queries.ts), same as the resident app does for its house list.
  return http.get<Organization[]>('/identity/organizations/', { query: { limit: 100 } });
}

export function fetchOrganization(organizationId: string): Promise<Organization> {
  return http.get<Organization>(`/identity/organizations/${organizationId}`);
}

export function registerOrganization(
  payload: OrganizationRegistrationPayload,
): Promise<OrganizationRegistrationResult> {
  return http.post<OrganizationRegistrationResult>('/identity/organizations/register', payload);
}

export function fetchOrganizationMembers(organizationId: string): Promise<OrganizationMember[]> {
  return http.get<OrganizationMember[]>(`/identity/organizations/${organizationId}/members/`, {
    query: { include_inactive: true },
  });
}

export function createOrganizationMemberAccount(
  organizationId: string,
  payload: StaffAccountPayload,
): Promise<OrganizationMember> {
  return http.post<OrganizationMember>(`/identity/organizations/${organizationId}/members/accounts`, payload);
}

export function deactivateOrganizationMember(organizationId: string, memberId: string): Promise<OrganizationMember> {
  return http.post<OrganizationMember>(`/identity/organizations/${organizationId}/members/${memberId}/deactivate`);
}
