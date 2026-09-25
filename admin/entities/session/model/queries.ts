import { useMutation, useQuery, useQueryClient, type QueryClient } from '@tanstack/react-query';

import {
  changePassword,
  fetchMe,
  fetchProfile,
  linkMaxAccount,
  staffLogin,
  unlinkMaxAccount,
  updateProfile,
} from '../api/staffAuth';
import { setSession } from './tokenStore';
import { useSession } from './useSession';

export const meQueryKey = ['session', 'me'] as const;
export const profileQueryKey = ['session', 'profile'] as const;

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
    onSuccess: () => invalidateOwnAccount(queryClient),
  });
}

export function useUnlinkMaxAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: unlinkMaxAccount,
    onSuccess: () => invalidateOwnAccount(queryClient),
  });
}

export function useProfile() {
  const { isAuthenticated } = useSession();
  return useQuery({ queryKey: profileQueryKey, queryFn: fetchProfile, enabled: isAuthenticated });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateProfile,
    onSuccess: (profile) => {
      queryClient.setQueryData(profileQueryKey, profile);
      // The name/e-mail also show up in the staff lists and on the home page.
      void queryClient.invalidateQueries({ queryKey: ['staff'] });
      void queryClient.invalidateQueries({ queryKey: ['organizations'] });
    },
  });
}

export function useChangePassword() {
  return useMutation({ mutationFn: changePassword });
}

function invalidateOwnAccount(queryClient: QueryClient) {
  void queryClient.invalidateQueries({ queryKey: profileQueryKey });
  return queryClient.invalidateQueries({ queryKey: ['organizations'] });
}
