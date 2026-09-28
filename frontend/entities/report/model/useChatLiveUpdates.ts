import { useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { http } from '@/shared/api';

import { latestChatChange } from '../lib/liveChat';
import { reportChatQueryKey } from './queries';
import type { ReportChatThread } from './types';

const RETRY_AFTER_ERROR_MS = 3000;

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
          await queryClient.refetchQueries({ queryKey: key, exact: true });
        }
        const thread = queryClient.getQueryData<ReportChatThread>(key);
        try {
          const { changed } = await http.get<{ changed: boolean }>(`/reports/${reportId}/messages/updates`, {
            query: { since: latestChatChange(thread?.messages ?? []) },
            signal: controller.signal,
          });
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
