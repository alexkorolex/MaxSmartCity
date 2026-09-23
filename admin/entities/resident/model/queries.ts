import { useQuery } from '@tanstack/react-query';

import { fetchResident, fetchResidents } from '../api/residents';

export const residentsQueryKey = (city?: string) => ['residents', city ?? ''] as const;
export const residentQueryKey = (residentId: string) => ['residents', 'member', residentId] as const;

export function useResidents(city?: string) {
  return useQuery({
    queryKey: residentsQueryKey(city),
    queryFn: () => fetchResidents({ city }),
  });
}

export function useResident(residentId: string) {
  return useQuery({
    queryKey: residentQueryKey(residentId),
    queryFn: () => fetchResident(residentId),
    enabled: Boolean(residentId),
  });
}
