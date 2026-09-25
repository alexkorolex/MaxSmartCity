import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchCities, fetchHouse, fetchHouseInfo, searchHouses } from '../api/houses';

export const citiesQueryKey = ['geo', 'cities'] as const;
export const houseSearchQueryKey = (city: string, query: string) => ['geo', 'houses', 'search', city, query] as const;
export const houseQueryKey = (houseId: string) => ['geo', 'houses', houseId] as const;
export const houseInfoQueryKey = (houseId: string) => ['geo', 'houses', houseId, 'info'] as const;

export function useCities() {
  return useQuery({ queryKey: citiesQueryKey, queryFn: fetchCities, staleTime: 30 * 60_000 });
}

export function useHouseSearch(city: string | null, query: string) {
  const normalized = query.trim();
  return useQuery({
    queryKey: houseSearchQueryKey(city ?? '', normalized),
    queryFn: () => searchHouses({ city: city ?? '', query: normalized }),
    enabled: Boolean(city),
    staleTime: 5 * 60_000,
    placeholderData: keepPreviousData,
  });
}

export function useHouse(houseId: string | null | undefined) {
  return useQuery({
    queryKey: houseQueryKey(houseId ?? ''),
    queryFn: () => fetchHouse(houseId ?? ''),
    enabled: Boolean(houseId),
    staleTime: 5 * 60_000,
  });
}

export function useHouseInfo(houseId: string | null | undefined) {
  return useQuery({
    queryKey: houseInfoQueryKey(houseId ?? ''),
    queryFn: () => fetchHouseInfo(houseId ?? ''),
    enabled: Boolean(houseId),
    staleTime: 5 * 60_000,
  });
}
