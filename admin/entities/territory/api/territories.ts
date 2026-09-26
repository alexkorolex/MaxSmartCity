import { http } from '@/shared/api';

import type {
  TerritoryAssignPayload,
  TerritoryCreatePayload,
  TerritoryHouse,
  TerritoryNode,
  TerritoryStreet,
  TerritoryUpdatePayload,
} from '../model/types';

export function fetchTerritories(): Promise<TerritoryNode[]> {
  return http.get<TerritoryNode[]>('/geo/territories/');
}

export function createTerritory(payload: TerritoryCreatePayload): Promise<TerritoryNode[]> {
  return http.post<TerritoryNode[]>('/geo/territories/', payload);
}

export function updateTerritory(territoryId: string, payload: TerritoryUpdatePayload): Promise<TerritoryNode[]> {
  return http.patch<TerritoryNode[]>(`/geo/territories/${territoryId}`, payload);
}

export function deleteTerritory(territoryId: string): Promise<void> {
  return http.delete<void>(`/geo/territories/${territoryId}`);
}

export function fetchTerritoryStreets(territoryId: string, q: string): Promise<TerritoryStreet[]> {
  return http.get<TerritoryStreet[]>(`/geo/territories/${territoryId}/streets`, { query: { q, limit: 1000 } });
}

export function fetchTerritoryStreetHouses(territoryId: string, street: string): Promise<TerritoryHouse[]> {
  return http.get<TerritoryHouse[]>(`/geo/territories/${territoryId}/houses`, { query: { street } });
}

export function assignToTerritory(territoryId: string, payload: TerritoryAssignPayload): Promise<{ moved: number }> {
  return http.post<{ moved: number }>(`/geo/territories/${territoryId}/assign`, payload);
}
