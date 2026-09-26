import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchChatConversations, fetchChatThread, sendChatMessage } from '../api/chat';

export const chatThreadQueryKey = (reportId: string) => ['chat', 'thread', reportId] as const;
export const chatConversationsQueryKey = ['chat', 'conversations'] as const;

/** Polls while the chat is open - reading is what spares the organization an e-mail/MAX
 * notification about a message it has already seen here. */
export function useChatThread(reportId: string) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: chatThreadQueryKey(reportId),
    queryFn: async () => {
      const thread = await fetchChatThread(reportId);
      // Fetching the thread just read the resident's messages - the inbox and the
      // sidebar badge shouldn't keep counting them until their own next poll.
      void queryClient.invalidateQueries({ queryKey: chatConversationsQueryKey });
      return thread;
    },
    enabled: Boolean(reportId),
    refetchInterval: 30_000, // safety net - live updates come from useChatLiveUpdates
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

export function useChatConversations() {
  return useQuery({ queryKey: chatConversationsQueryKey, queryFn: fetchChatConversations, refetchInterval: 20_000 });
}
