import { http } from '@/shared/api';

import type { House } from '../model/types';

export function fetchHouses(): Promise<House[]> {
  return http.get<House[]>('/geo/houses');
}
