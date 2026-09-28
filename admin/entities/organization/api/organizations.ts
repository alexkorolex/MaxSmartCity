import { http } from '@/shared/api';

import type {
  AuthorityRegistrationPayload,
  Organization,
  OrganizationMember,
  OrganizationRegistrationPayload,
  OrganizationRegistrationResult,
  StaffAccountCreatedResult,
  StaffAccountPayload,
} from '../model/types';

export function fetchOrganizations(): Promise<Organization[]> {
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

export function registerAuthority(payload: AuthorityRegistrationPayload): Promise<OrganizationRegistrationResult> {
  return http.post<OrganizationRegistrationResult>('/identity/organizations/authorities', payload);
}

export function fetchOrganizationMembers(organizationId: string): Promise<OrganizationMember[]> {
  return http.get<OrganizationMember[]>(`/identity/organizations/${organizationId}/members/`, {
    query: { include_inactive: true },
  });
}

export function createOrganizationMemberAccount(
  organizationId: string,
  payload: StaffAccountPayload,
): Promise<StaffAccountCreatedResult> {
  return http.post<StaffAccountCreatedResult>(`/identity/organizations/${organizationId}/members/accounts`, payload);
}

export function deactivateOrganizationMember(organizationId: string, memberId: string): Promise<OrganizationMember> {
  return http.post<OrganizationMember>(`/identity/organizations/${organizationId}/members/${memberId}/deactivate`);
}
