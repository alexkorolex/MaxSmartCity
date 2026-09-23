import { http } from '@/shared/api';

export function fetchCities(): Promise<string[]> {
  return http.get<string[]>('/geo/addresses/cities');
}
