import { http } from '@/shared/api';
import { API_BASE_URL } from '@/shared/config';

import type { DistrictCollection, IncidentHouseCollection, MapSummary } from '../model/types';

export function fetchMapSummary(): Promise<MapSummary> {
  return http.get<MapSummary>('/map/summary');
}

export function fetchMapDistricts(): Promise<DistrictCollection> {
  return http.get<DistrictCollection>('/map/districts');
}

export function fetchIncidentHouses(includeClosed: boolean): Promise<IncidentHouseCollection> {
  return http.get<IncidentHouseCollection>('/map/incidents', { query: { include_closed: includeClosed } });
}

export function mapTileUrl(layer: 'houses' | 'buildings'): string {
  return `${window.location.origin}${API_BASE_URL}/map/tiles/${layer}/{z}/{x}/{y}`;
}

export function isMapApiUrl(url: string): boolean {
  return url.startsWith(`${window.location.origin}${API_BASE_URL}/map/`);
}
