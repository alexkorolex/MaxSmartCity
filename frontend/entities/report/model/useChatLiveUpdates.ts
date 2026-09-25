import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { http } from '@/shared/api';

import { latestChatChange } from '../lib/liveChat';
import { reportChatQueryKey } from './queries';
import type { ReportChatThread } from './types';

const RETRY_AFTER_ERROR_MS = 3000;

/** Resolves once the page is visible again (or the loop is aborted). */
function untilVisible(signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const done = () => {
      if (document.hidden && !signal.aborted) return;
      document.removeEventListener('visibilitychange', done);
      signal.removeEventListener('abort', done);
      resolve();
    };
    document.addEventListener('visibilitychange', done);
    signal.addEventListener('abort', done);
  });
}

/**
 * Keeps the chat live while it's open: a long poll the server answers the moment the
 * organization writes or reads, after which the thread is refetched. The regular poll in
 * `useReportChat` only remains as a safety net.
 *
 * Paused while the page is hidden: fetching the thread marks messages read, and an unread
 * message is what gets the other side's notification out - a chat left in a background
 * tab (or a minimised MAX mini-app) mustn't swallow it.
 */
export function useChatLiveUpdates(reportId: string, ready: boolean): void {
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!reportId || !ready) return undefined;
    const controller = new AbortController();
    const key = reportChatQueryKey(reportId);

    void (async () => {
      while (!controller.signal.aborted) {
        if (document.hidden) {
          await untilVisible(controller.signal);
          if (controller.signal.aborted) return;
          // Back in the chat: show (and mark read) whatever came in meanwhile.
          await queryClient.refetchQueries({ queryKey: key, exact: true });
        }
        const thread = queryClient.getQueryData<ReportChatThread>(key);
        try {
          const { changed } = await http.get<{ changed: boolean }>(`/reports/${reportId}/messages/updates`, {
            query: { since: latestChatChange(thread?.messages ?? []) },
            signal: controller.signal,
          });
          // Hidden meanwhile: the refetch waits for the page to come back (top of the loop).
          if (changed && !document.hidden) await queryClient.refetchQueries({ queryKey: key, exact: true });
        } catch {
          if (controller.signal.aborted) return;
          await new Promise((resolve) => setTimeout(resolve, RETRY_AFTER_ERROR_MS));
        }
      }
    })();

    return () => controller.abort();
  }, [queryClient, reportId, ready]);
}
