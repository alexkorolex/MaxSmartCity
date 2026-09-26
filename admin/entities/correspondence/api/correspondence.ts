import { http } from '@/shared/api';

import type {
  ConversationSummary,
  ConversationThread,
  CorrespondenceContact,
  StartConversationPayload,
} from '../model/types';

export function fetchContacts(): Promise<CorrespondenceContact[]> {
  return http.get<CorrespondenceContact[]>('/correspondence/contacts');
}

export function fetchConversations(): Promise<ConversationSummary[]> {
  return http.get<ConversationSummary[]>('/correspondence/conversations');
}

export function fetchConversation(conversationId: string): Promise<ConversationThread> {
  return http.get<ConversationThread>(`/correspondence/conversations/${conversationId}`);
}

export function startConversation(payload: StartConversationPayload): Promise<ConversationThread> {
  return http.post<ConversationThread>('/correspondence/conversations', payload);
}

export function sendConversationMessage(conversationId: string, text: string): Promise<ConversationThread> {
  return http.post<ConversationThread>(`/correspondence/conversations/${conversationId}/messages`, { text });
}

export function waitForConversationUpdates(
  conversationId: string,
  since: string | null,
  signal: AbortSignal,
): Promise<{ changed: boolean }> {
  return http.get<{ changed: boolean }>(`/correspondence/conversations/${conversationId}/updates`, {
    query: { since },
    signal,
  });
}
