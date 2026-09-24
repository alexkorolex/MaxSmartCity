import { http } from '@/shared/api';

import type { House, HouseInfo } from '../model/types';

export function fetchHouses(): Promise<House[]> {
  return http.get<House[]>('/geo/houses');
}

export function fetchHouseInfo(houseId: string): Promise<HouseInfo> {
  return http.get<HouseInfo>(`/geo/houses/${houseId}/info`);
}
