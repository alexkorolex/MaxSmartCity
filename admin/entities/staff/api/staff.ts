import { http } from '@/shared/api';

import type { StaffMember } from '../model/types';

interface ListParams {
  city?: string;
  organizationId?: string;
  limit?: number;
  offset?: number;
}

export function fetchStaff(params: ListParams = {}): Promise<StaffMember[]> {
  return http.get<StaffMember[]>('/identity/operator-users/', {
    query: {
      city: params.city,
      organization_id: params.organizationId,
      limit: params.limit ?? 100,
      offset: params.offset,
    },
  });
}

export function fetchStaffMember(staffId: string): Promise<StaffMember> {
  return http.get<StaffMember>(`/identity/operator-users/${staffId}`);
}
