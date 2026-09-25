import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  createOrganizationChannel,
  deleteOrganizationChannel,
  fetchOrganizationChannels,
  setOrganizationChannelActive,
  testOrganizationChannel,
} from '../api/channels';
import type { OrganizationChannelPayload } from './types';

export const organizationChannelsQueryKey = (organizationId: string) =>
  ['notification-channels', organizationId] as const;

export function useOrganizationChannels(organizationId: string) {
  return useQuery({
    queryKey: organizationChannelsQueryKey(organizationId),
    queryFn: () => fetchOrganizationChannels(organizationId),
    enabled: Boolean(organizationId),
  });
}

function useInvalidate(organizationId: string) {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: organizationChannelsQueryKey(organizationId) });
}

export function useCreateOrganizationChannel(organizationId: string) {
  const invalidate = useInvalidate(organizationId);
  return useMutation({
    mutationFn: (payload: OrganizationChannelPayload) => createOrganizationChannel(payload),
    onSuccess: invalidate,
  });
}

export function useSetOrganizationChannelActive(organizationId: string) {
  const invalidate = useInvalidate(organizationId);
  return useMutation({
    mutationFn: ({ channelId, active }: { channelId: string; active: boolean }) =>
      setOrganizationChannelActive(channelId, active),
    onSuccess: invalidate,
  });
}

export function useDeleteOrganizationChannel(organizationId: string) {
  const invalidate = useInvalidate(organizationId);
  return useMutation({
    mutationFn: (channelId: string) => deleteOrganizationChannel(channelId),
    onSuccess: invalidate,
  });
}

export function useTestOrganizationChannel() {
  return useMutation({ mutationFn: (channelId: string) => testOrganizationChannel(channelId) });
}
