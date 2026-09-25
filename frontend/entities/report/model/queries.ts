import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  closeReport,
  fetchReportChat,
  sendReportChatMessage,
  createReport,
  fetchMyReports,
  fetchProblemCategories,
  fetchReport,
  fetchReportAttachments,
  uploadReportAttachment,
} from '../api/reports';
import type { ReportCreatePayload } from './types';

export const myReportsQueryKey = ['reports', 'mine'] as const;
export const reportQueryKey = (reportId: string) => ['reports', reportId] as const;
export const problemCategoriesQueryKey = ['reports', 'categories'] as const;
export const reportAttachmentsQueryKey = (reportId: string) => ['reports', reportId, 'attachments'] as const;

export function useMyReports() {
  return useQuery({ queryKey: myReportsQueryKey, queryFn: fetchMyReports });
}

export function useReport(reportId: string) {
  return useQuery({ queryKey: reportQueryKey(reportId), queryFn: () => fetchReport(reportId) });
}

export function useProblemCategories() {
  return useQuery({ queryKey: problemCategoriesQueryKey, queryFn: fetchProblemCategories });
}

export function useReportAttachments(reportId: string) {
  return useQuery({
    queryKey: reportAttachmentsQueryKey(reportId),
    queryFn: () => fetchReportAttachments(reportId),
    enabled: Boolean(reportId),
  });
}

export function useUploadReportAttachment(reportId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadReportAttachment(reportId, file),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: reportAttachmentsQueryKey(reportId) });
    },
  });
}

export function useCreateReport() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ReportCreatePayload) => createReport(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: myReportsQueryKey });
    },
  });
}

export function useCloseReport(reportId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (comment: string | null) => closeReport(reportId, comment),
    onSuccess: () => {
      // The incident (my house) and notifications can change along with the report.
      for (const key of [['reports'], ['incidents'], ['notifications']]) {
        void queryClient.invalidateQueries({ queryKey: key });
      }
    },
  });
}

export const reportChatQueryKey = (reportId: string) => ['reports', reportId, 'chat'] as const;
const CHAT_POLL_MS = 30_000; // safety net - live updates come from useChatLiveUpdates

/** Polls while the chat is on screen - that's also what marks new messages as read, so the
 * resident isn't pinged in MAX about messages they've already seen here. */
export function useReportChat(reportId: string) {
  return useQuery({
    queryKey: reportChatQueryKey(reportId),
    queryFn: () => fetchReportChat(reportId),
    enabled: Boolean(reportId),
    refetchInterval: CHAT_POLL_MS,
    refetchIntervalInBackground: false,
  });
}

export function useSendReportChatMessage(reportId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => sendReportChatMessage(reportId, text),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: reportChatQueryKey(reportId) }),
  });
}
