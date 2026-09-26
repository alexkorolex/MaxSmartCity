import { http } from '@/shared/api';

import type { TerritorySummary } from '../model/types';

export function fetchTerritorySummary(territoryId: string): Promise<TerritorySummary> {
  return http.get<TerritorySummary>(`/analytics/territories/${territoryId}/summary`);
}
