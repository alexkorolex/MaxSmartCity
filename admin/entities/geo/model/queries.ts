import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchCities } from '../api/geo';
import { assignHouseManagement, fetchHouseManagement, searchHouses, terminateHouseManagement } from '../api/houses';
import type { AssignHouseManagementPayload } from './types';

export const citiesQueryKey = ['cities'] as const;
export const houseManagementQueryKey = (organizationId?: string) =>
  ['house-management', organizationId ?? ''] as const;
export const houseSearchQueryKey = (q: string, city: string) => ['houses', 'search', q, city] as const;

export function useCities() {
  return useQuery({ queryKey: citiesQueryKey, queryFn: fetchCities, staleTime: 5 * 60_000 });
}

export function useHouseManagement(organizationId?: string) {
  return useQuery({
    queryKey: houseManagementQueryKey(organizationId),
    queryFn: () => fetchHouseManagement({ organizationId }),
  });
}

/** Address search for the "take a house" picker - only runs once there's something to search. */
export function useHouseSearch(q: string, city: string) {
  const query = q.trim();
  return useQuery({
    queryKey: houseSearchQueryKey(query, city),
    queryFn: () => searchHouses({ q: query, city: city || undefined }),
    enabled: query.length >= 2,
  });
}

function useInvalidateHouses() {
  const queryClient = useQueryClient();
  return () => {
    // Houses define what an organization sees - residents, reports and incidents too.
    for (const key of [['house-management'], ['houses'], ['residents'], ['reports'], ['incidents']]) {
      void queryClient.invalidateQueries({ queryKey: key });
    }
  };
}

export function useAssignHouseManagement() {
  const invalidate = useInvalidateHouses();
  return useMutation({
    mutationFn: (payload: AssignHouseManagementPayload) => assignHouseManagement(payload),
    onSuccess: invalidate,
  });
}

export function useTerminateHouseManagement() {
  const invalidate = useInvalidateHouses();
  return useMutation({
    mutationFn: ({ managementId, reason }: { managementId: string; reason?: string }) =>
      terminateHouseManagement(managementId, reason),
    onSuccess: invalidate,
  });
}
