import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  closeReport,
  fetchReportChat,
  sendReportChatMessage,
  createReport,
  decideReportGrouping,
  fetchReportGrouping,
  fetchMyReports,
  fetchProblemCategories,
  fetchReport,
  fetchReportAttachments,
  uploadReportAttachment,
} from '../api/reports';
import type { GroupingDecision, ReportCreatePayload } from './types';

export const myReportsQueryKey = ['reports', 'mine'] as const;
export const reportQueryKey = (reportId: string) => ['reports', reportId] as const;
export const problemCategoriesQueryKey = ['reports', 'categories'] as const;
export const reportGroupingQueryKey = (reportId: string) => ['reports', reportId, 'grouping'] as const;
export const reportAttachmentsQueryKey = (reportId: string) => ['reports', reportId, 'attachments'] as const;

export function useMyReports() {
  return useQuery({ queryKey: myReportsQueryKey, queryFn: fetchMyReports });
}

export function useReport(reportId: string) {
  return useQuery({ queryKey: reportQueryKey(reportId), queryFn: () => fetchReport(reportId) });
}

export function useReportGrouping(reportId: string, enabled: boolean) {
  return useQuery({
    queryKey: reportGroupingQueryKey(reportId),
    queryFn: () => fetchReportGrouping(reportId),
    enabled: Boolean(reportId) && enabled,
  });
}

export function useDecideReportGrouping(reportId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (decision: GroupingDecision) => decideReportGrouping(reportId, decision),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['reports'] });
      void queryClient.invalidateQueries({ queryKey: ['incidents'] });
    },
  });
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
      for (const key of [['reports'], ['incidents'], ['notifications']]) {
        void queryClient.invalidateQueries({ queryKey: key });
      }
    },
  });
}

export const reportChatQueryKey = (reportId: string) => ['reports', reportId, 'chat'] as const;
const CHAT_POLL_MS = 30_000;

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
