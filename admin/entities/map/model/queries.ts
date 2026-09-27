import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchIncidentHouses, fetchMapDistricts, fetchMapSummary } from '../api/map';

const REFRESH_INTERVAL_MS = 60_000;

export function useMapSummary() {
  return useQuery({ queryKey: ['map', 'summary'], queryFn: fetchMapSummary, staleTime: 5 * 60_000 });
}

export function useMapDistricts() {
  return useQuery({
    queryKey: ['map', 'districts'],
    queryFn: fetchMapDistricts,
    refetchInterval: REFRESH_INTERVAL_MS,
  });
}

export function useIncidentHouses(includeClosed: boolean) {
  return useQuery({
    queryKey: ['map', 'incidents', includeClosed],
    queryFn: () => fetchIncidentHouses(includeClosed),
    refetchInterval: REFRESH_INTERVAL_MS,
    placeholderData: keepPreviousData,
  });
}
