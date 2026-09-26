import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { fetchTerritorySummary } from '../api/analytics';

export function useTerritorySummary(territoryId: string | null) {
  return useQuery({
    queryKey: ['analytics', 'territory', territoryId],
    queryFn: () => fetchTerritorySummary(territoryId ?? ''),
    enabled: Boolean(territoryId),
    placeholderData: keepPreviousData,
  });
}
