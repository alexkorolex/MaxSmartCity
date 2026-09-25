import { http } from '@/shared/api';

import type { ChatConversation, ChatMessage, ChatThread } from '../model/types';

/** Opening the chat (as the organization) marks the resident's messages as read. */
export function fetchChatThread(reportId: string): Promise<ChatThread> {
  return http.get<ChatThread>(`/reports/${reportId}/messages`);
}

export function sendChatMessage(reportId: string, text: string): Promise<ChatMessage> {
  return http.post<ChatMessage>(`/reports/${reportId}/messages`, { text });
}

export function fetchChatConversations(): Promise<ChatConversation[]> {
  return http.get<ChatConversation[]>('/chat/conversations', { query: { limit: 100 } });
}
