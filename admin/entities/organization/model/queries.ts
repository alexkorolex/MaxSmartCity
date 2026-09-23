import { useQuery } from '@tanstack/react-query';

import { fetchOrganization, fetchOrganizations } from '../api/organizations';

export const organizationsQueryKey = ['organizations'] as const;
export const organizationQueryKey = (organizationId: string) => ['organizations', organizationId] as const;

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
