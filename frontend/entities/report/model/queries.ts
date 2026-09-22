import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createReport, fetchMyReports, fetchProblemCategories, fetchReport } from '../api/reports';
import type { ReportCreatePayload } from './types';

export const myReportsQueryKey = ['reports', 'mine'] as const;
export const reportQueryKey = (reportId: string) => ['reports', reportId] as const;
export const problemCategoriesQueryKey = ['reports', 'categories'] as const;

export function useMyReports() {
  return useQuery({ queryKey: myReportsQueryKey, queryFn: fetchMyReports });
}

export function useReport(reportId: string) {
  return useQuery({ queryKey: reportQueryKey(reportId), queryFn: () => fetchReport(reportId) });
}

export function useProblemCategories() {
  return useQuery({ queryKey: problemCategoriesQueryKey, queryFn: fetchProblemCategories });
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
