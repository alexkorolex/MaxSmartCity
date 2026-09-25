import { http } from '@/shared/api';

import type { AssignHouseManagementPayload, House, HouseInfo, HouseManagement } from '../model/types';

export function searchHouses(params: { q?: string; city?: string }): Promise<House[]> {
  return http.get<House[]>('/geo/houses/', { query: { q: params.q, city: params.city, limit: 50 } });
}

/** Reference data about a house: its management company from open sources with requisites
 * and contacts, plus the platform organization managing it (if any). */
export function fetchHouseInfo(houseId: string): Promise<HouseInfo> {
  return http.get<HouseInfo>(`/geo/houses/${houseId}/info`);
}

export function fetchHouseManagement(params: { organizationId?: string } = {}): Promise<HouseManagement[]> {
  // Scoped server-side: a housing worker only ever gets their own organization's houses.
  return http.get<HouseManagement[]>('/geo/house-management/', {
    query: { organization_id: params.organizationId, limit: 200 },
  });
}

export function assignHouseManagement(payload: AssignHouseManagementPayload): Promise<HouseManagement> {
  return http.post<HouseManagement>('/geo/house-management/', payload);
}

export function terminateHouseManagement(managementId: string, reason?: string): Promise<HouseManagement> {
  return http.post<HouseManagement>(`/geo/house-management/${managementId}/terminate`, { reason: reason ?? null });
}
