import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchChatConversations, fetchChatThread, sendChatMessage } from '../api/chat';

export const chatThreadQueryKey = (reportId: string) => ['chat', 'thread', reportId] as const;
export const chatConversationsQueryKey = ['chat', 'conversations'] as const;

export function useChatThread(reportId: string) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: chatThreadQueryKey(reportId),
    queryFn: async () => {
      const thread = await fetchChatThread(reportId);
      void queryClient.invalidateQueries({ queryKey: chatConversationsQueryKey });
      return thread;
    },
    enabled: Boolean(reportId),
    refetchInterval: 30_000,
  });
}

export function useSendChatMessage(reportId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => sendChatMessage(reportId, text),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: chatThreadQueryKey(reportId) });
      void queryClient.invalidateQueries({ queryKey: chatConversationsQueryKey });
    },
  });
}

export function useChatConversations(enabled = true) {
  return useQuery({
    queryKey: chatConversationsQueryKey,
    queryFn: fetchChatConversations,
    refetchInterval: 20_000,
    enabled,
  });
}
