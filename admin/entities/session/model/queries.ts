import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchMe, linkMaxAccount, staffLogin } from '../api/staffAuth';
import { setSession } from './tokenStore';
import { useSession } from './useSession';

export const meQueryKey = ['session', 'me'] as const;

export function useMe() {
  const { isAuthenticated } = useSession();
  return useQuery({ queryKey: meQueryKey, queryFn: fetchMe, enabled: isAuthenticated });
}

export function useStaffLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      staffLogin(username, password),
    onSuccess: (response) => {
      setSession(response);
      void queryClient.invalidateQueries({ queryKey: meQueryKey });
    },
  });
}

export function useLinkMaxAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (maxUserId: number) => linkMaxAccount(maxUserId),
    // `has_max_account` in the organization's member list changes.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['organizations'] }),
  });
}
