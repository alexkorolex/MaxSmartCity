import { http } from '@/shared/api';

import type {
  ChatMessage,
  CloseReportResult,
  ProblemCategory,
  Report,
  ReportAttachment,
  ReportChatThread,
  ReportCreatePayload,
  ReportCreateResult,
  GroupingResult,
  GroupingDecision,
} from '../model/types';

export function fetchMyReports(): Promise<Report[]> {
  return http.get<Report[]>('/reports/mine');
}

export function fetchReport(reportId: string): Promise<Report> {
  return http.get<Report>(`/reports/${reportId}`);
}

export function createReport(payload: ReportCreatePayload): Promise<ReportCreateResult> {
  return http.post<ReportCreateResult>('/reports/intake', payload);
}

export function fetchReportGrouping(reportId: string): Promise<GroupingResult> {
  return http.get<GroupingResult>(`/reports/${reportId}/grouping`);
}

export function decideReportGrouping(reportId: string, decision: GroupingDecision): Promise<GroupingResult> {
  return http.post<GroupingResult>(`/reports/${reportId}/grouping-decision`, decision);
}

export function fetchProblemCategories(): Promise<ProblemCategory[]> {
  return http.get<ProblemCategory[]>('/reports/categories/', { query: { limit: 100 } });
}

export function uploadReportAttachment(reportId: string, file: File): Promise<ReportAttachment> {
  const formData = new FormData();
  formData.set('file', file);
  return http.post<ReportAttachment>(`/reports/${reportId}/attachments`, formData);
}

export function fetchReportAttachments(reportId: string): Promise<ReportAttachment[]> {
  return http.get<ReportAttachment[]>(`/reports/${reportId}/attachments`);
}

export function closeReport(reportId: string, comment: string | null): Promise<CloseReportResult> {
  return http.post<CloseReportResult>(`/reports/${reportId}/close`, { comment });
}

export function fetchReportChat(reportId: string): Promise<ReportChatThread> {
  return http.get<ReportChatThread>(`/reports/${reportId}/messages`);
}

export function sendReportChatMessage(reportId: string, text: string): Promise<ChatMessage> {
  return http.post<ChatMessage>(`/reports/${reportId}/messages`, { text });
}
