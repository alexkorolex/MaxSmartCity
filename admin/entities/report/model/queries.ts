import { useQuery } from '@tanstack/react-query';

import { fetchProblemCategories, fetchReport, fetchReports } from '../api/reports';

export const reportsQueryKey = (residentId?: string, city?: string) =>
  ['reports', residentId ?? '', city ?? ''] as const;
export const reportQueryKey = (reportId: string) => ['reports', 'member', reportId] as const;
export const problemCategoriesQueryKey = ['problem-categories'] as const;

export function useReports(params: { residentId?: string; city?: string } = {}) {
  return useQuery({
    queryKey: reportsQueryKey(params.residentId, params.city),
    queryFn: () => fetchReports(params),
  });
}

export function useReport(reportId: string) {
  return useQuery({
    queryKey: reportQueryKey(reportId),
    queryFn: () => fetchReport(reportId),
    enabled: Boolean(reportId),
  });
}

export function useProblemCategories() {
  return useQuery({
    queryKey: problemCategoriesQueryKey,
    queryFn: fetchProblemCategories,
    staleTime: 60_000,
  });
}
