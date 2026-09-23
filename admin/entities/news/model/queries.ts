import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createNewsItem, deleteNewsItem, fetchNews, fetchNewsItem, updateNewsItem } from '../api/news';
import type { NewsPostCreatePayload, NewsPostUpdatePayload } from './types';

export const newsListQueryKey = ['news'] as const;
export const newsItemQueryKey = (newsId: string) => ['news', newsId] as const;

export function useNewsList() {
  return useQuery({ queryKey: newsListQueryKey, queryFn: fetchNews });
}

export function useNewsItem(newsId: string) {
  return useQuery({
    queryKey: newsItemQueryKey(newsId),
    queryFn: () => fetchNewsItem(newsId),
    enabled: Boolean(newsId),
  });
}

export function useCreateNews() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: NewsPostCreatePayload) => createNewsItem(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: newsListQueryKey }),
  });
}

export function useUpdateNews(newsId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: NewsPostUpdatePayload) => updateNewsItem(newsId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: newsListQueryKey });
      queryClient.invalidateQueries({ queryKey: newsItemQueryKey(newsId) });
    },
  });
}

export function useDeleteNews() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (newsId: string) => deleteNewsItem(newsId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: newsListQueryKey }),
  });
}
