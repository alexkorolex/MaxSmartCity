import { useQuery } from '@tanstack/react-query';

import { fetchCities } from '../api/geo';

export const citiesQueryKey = ['cities'] as const;

export function useCities() {
  return useQuery({ queryKey: citiesQueryKey, queryFn: fetchCities, staleTime: 5 * 60_000 });
}
