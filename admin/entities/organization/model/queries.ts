import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createOrganizationMemberAccount,
  deactivateOrganizationMember,
  fetchOrganization,
  fetchOrganizationMembers,
  fetchOrganizations,
  registerOrganization,
} from '../api/organizations';
import type { OrganizationRegistrationPayload, StaffAccountPayload } from './types';

export const organizationsQueryKey = ['organizations'] as const;
export const organizationQueryKey = (organizationId: string) => ['organizations', organizationId] as const;
export const organizationMembersQueryKey = (organizationId: string) =>
  ['organizations', organizationId, 'members'] as const;

export function useOrganizations() {
  return useQuery({ queryKey: organizationsQueryKey, queryFn: fetchOrganizations, staleTime: 60_000 });
}

export function useOrganization(organizationId: string) {
  return useQuery({
    queryKey: organizationQueryKey(organizationId),
    queryFn: () => fetchOrganization(organizationId),
    enabled: Boolean(organizationId),
  });
}

export function useOrganizationMembers(organizationId: string) {
  return useQuery({
    queryKey: organizationMembersQueryKey(organizationId),
    queryFn: () => fetchOrganizationMembers(organizationId),
    enabled: Boolean(organizationId),
  });
}

export function useRegisterOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: OrganizationRegistrationPayload) => registerOrganization(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: organizationsQueryKey });
      void queryClient.invalidateQueries({ queryKey: ['staff'] });
    },
  });
}

export function useCreateOrganizationMemberAccount(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: StaffAccountPayload) => createOrganizationMemberAccount(organizationId, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: organizationMembersQueryKey(organizationId) });
      void queryClient.invalidateQueries({ queryKey: ['staff'] });
    },
  });
}

export function useDeactivateOrganizationMember(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (memberId: string) => deactivateOrganizationMember(organizationId, memberId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: organizationMembersQueryKey(organizationId) });
      void queryClient.invalidateQueries({ queryKey: ['staff'] });
    },
  });
}
