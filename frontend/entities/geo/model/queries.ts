import { useQuery } from '@tanstack/react-query';

import { fetchHouseInfo, fetchHouses } from '../api/houses';

export const housesQueryKey = ['geo', 'houses'] as const;
export const houseInfoQueryKey = (houseId: string) => ['geo', 'houses', houseId, 'info'] as const;

export function useHouses() {
  return useQuery({ queryKey: housesQueryKey, queryFn: fetchHouses, staleTime: 5 * 60_000 });
}

export function useHouseInfo(houseId: string | null | undefined) {
  return useQuery({
    queryKey: houseInfoQueryKey(houseId ?? ''),
    queryFn: () => fetchHouseInfo(houseId ?? ''),
    enabled: Boolean(houseId),
    staleTime: 5 * 60_000,
  });
}
