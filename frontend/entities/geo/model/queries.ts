import { useQuery } from '@tanstack/react-query';

import { fetchHouses } from '../api/houses';

export const housesQueryKey = ['geo', 'houses'] as const;

export function useHouses() {
  return useQuery({ queryKey: housesQueryKey, queryFn: fetchHouses, staleTime: 5 * 60_000 });
}
