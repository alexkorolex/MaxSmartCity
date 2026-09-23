import { http } from '@/shared/api';

import type { ProblemCategory, Report, ReportAttachment } from '../model/types';

interface ListParams {
  residentId?: string;
  city?: string;
  limit?: number;
  offset?: number;
}

export function fetchReports(params: ListParams = {}): Promise<Report[]> {
  return http.get<Report[]>('/reports/', {
    query: {
      resident_id: params.residentId,
      city: params.city,
      limit: params.limit ?? 100,
      offset: params.offset,
    },
  });
}

export function fetchReport(reportId: string): Promise<Report> {
  return http.get<Report>(`/reports/${reportId}`);
}

export function fetchProblemCategories(): Promise<ProblemCategory[]> {
  return http.get<ProblemCategory[]>('/reports/categories/', { query: { limit: 100 } });
}

export function fetchReportAttachments(reportId: string): Promise<ReportAttachment[]> {
  return http.get<ReportAttachment[]>(`/reports/${reportId}/attachments`);
}
