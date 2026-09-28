import { http } from '@/shared/api';

import type { House, HouseInfo } from '../model/types';

export const HOUSE_SEARCH_LIMIT = 50;

export function fetchCities(): Promise<string[]> {
  return http.get<string[]>('/geo/addresses/cities');
}

export function searchHouses(params: { city: string; query: string }): Promise<House[]> {
  return http.get<House[]>('/geo/houses', {
    query: { city: params.city, q: params.query || undefined, limit: HOUSE_SEARCH_LIMIT },
  });
}

export function fetchHouse(houseId: string): Promise<House> {
  return http.get<House>(`/geo/houses/${houseId}`);
}

export function fetchHouseInfo(houseId: string): Promise<HouseInfo> {
  return http.get<HouseInfo>(`/geo/houses/${houseId}/info`);
}
