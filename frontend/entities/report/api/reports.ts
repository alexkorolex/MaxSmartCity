import { http } from '@/shared/api';

import type { ProblemCategory, Report, ReportAttachment, ReportCreatePayload } from '../model/types';

export function fetchMyReports(): Promise<Report[]> {
  return http.get<Report[]>('/reports/mine');
}

export function fetchReport(reportId: string): Promise<Report> {
  return http.get<Report>(`/reports/${reportId}`);
}

export function createReport(payload: ReportCreatePayload): Promise<Report> {
  return http.post<Report>('/reports/', payload);
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
