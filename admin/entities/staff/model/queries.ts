import { useQuery } from '@tanstack/react-query';

import { fetchStaff, fetchStaffDirectory, fetchStaffMember } from '../api/staff';

export const staffQueryKey = (city?: string, organizationId?: string) =>
  ['staff', city ?? '', organizationId ?? ''] as const;
export const staffMemberQueryKey = (staffId: string) => ['staff', 'member', staffId] as const;

export function useStaffList(city?: string, organizationId?: string) {
  return useQuery({
    queryKey: staffQueryKey(city, organizationId),
    queryFn: () => fetchStaff({ city, organizationId }),
  });
}

export function useStaffMember(staffId: string) {
  return useQuery({
    queryKey: staffMemberQueryKey(staffId),
    queryFn: () => fetchStaffMember(staffId),
    enabled: Boolean(staffId),
  });
}

export function useStaffDirectory(organizationId?: string, enabled = true) {
  return useQuery({
    queryKey: ['staff', 'directory', organizationId ?? ''],
    queryFn: () => fetchStaffDirectory(organizationId),
    enabled,
  });
}
