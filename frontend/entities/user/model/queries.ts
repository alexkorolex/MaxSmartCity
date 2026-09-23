import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchMyProfile, updateMyProfile } from '../api/residentProfile';
import type { ResidentSelfUpdate } from './types';

export const myProfileQueryKey = ['user', 'me'] as const;

export function useMyProfile() {
  return useQuery({ queryKey: myProfileQueryKey, queryFn: fetchMyProfile });
}

export function useUpdateMyProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (patch: ResidentSelfUpdate) => updateMyProfile(patch),
    onSuccess: (profile) => {
      queryClient.setQueryData(myProfileQueryKey, profile);
    },
  });
}
