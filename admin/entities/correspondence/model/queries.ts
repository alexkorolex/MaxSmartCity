import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import {
  fetchContacts,
  fetchConversation,
  fetchConversations,
  sendConversationMessage,
  startConversation,
  waitForConversationUpdates,
} from '../api/correspondence';
import type { ConversationThread, StartConversationPayload } from './types';

export const conversationsQueryKey = ['correspondence', 'conversations'] as const;
export const conversationQueryKey = (conversationId: string) => ['correspondence', 'conversation', conversationId] as const;

const RETRY_AFTER_ERROR_MS = 3000;

export function useCorrespondenceContacts() {
  return useQuery({ queryKey: ['correspondence', 'contacts'], queryFn: fetchContacts, staleTime: 60_000 });
}

export function useConversations() {
  return useQuery({ queryKey: conversationsQueryKey, queryFn: fetchConversations, refetchInterval: 20_000 });
}

export function useConversation(conversationId: string) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: conversationQueryKey(conversationId),
    queryFn: async () => {
      const thread = await fetchConversation(conversationId);
      void queryClient.invalidateQueries({ queryKey: conversationsQueryKey });
      return thread;
    },
    enabled: Boolean(conversationId),
    refetchInterval: 30_000,
  });
}

export function useStartConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: StartConversationPayload) => startConversation(payload),
    onSuccess: (thread) => {
      queryClient.setQueryData(conversationQueryKey(thread.id), thread);
      void queryClient.invalidateQueries({ queryKey: conversationsQueryKey });
    },
  });
}

export function useSendConversationMessage(conversationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => sendConversationMessage(conversationId, text),
    onSuccess: (thread) => {
      queryClient.setQueryData(conversationQueryKey(conversationId), thread);
      void queryClient.invalidateQueries({ queryKey: conversationsQueryKey });
    },
  });
}

function latestChange(thread: ConversationThread | undefined): string | null {
  const moments = [
    ...(thread?.messages.map((message) => message.created_at) ?? []),
    ...(thread?.counterpart_read_at ? [thread.counterpart_read_at] : []),
  ];
  return moments.reduce<string | null>(
    (latest, value) => (latest === null || Date.parse(value) > Date.parse(latest) ? value : latest),
    null,
  );
}

export function useConversationLiveUpdates(conversationId: string, ready: boolean): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!conversationId || !ready) return undefined;
    const controller = new AbortController();
    const key = conversationQueryKey(conversationId);

    void (async () => {
      while (!controller.signal.aborted) {
        const since = latestChange(queryClient.getQueryData<ConversationThread>(key));
        try {
          const { changed } = await waitForConversationUpdates(conversationId, since, controller.signal);
          if (changed && !document.hidden) await queryClient.refetchQueries({ queryKey: key, exact: true });
          if (document.hidden) await new Promise((resolve) => setTimeout(resolve, RETRY_AFTER_ERROR_MS));
        } catch {
          if (controller.signal.aborted) return;
          await new Promise((resolve) => setTimeout(resolve, RETRY_AFTER_ERROR_MS));
        }
      }
    })();

    return () => controller.abort();
  }, [queryClient, conversationId, ready]);
}
