import { useQuery } from '@tanstack/react-query';

import { fetchNews, fetchNewsItem } from '../api/news';

export const newsListQueryKey = ['news'] as const;
export const newsItemQueryKey = (newsId: string) => ['news', newsId] as const;

export function useNewsList() {
  return useQuery({ queryKey: newsListQueryKey, queryFn: fetchNews });
}

export function useNewsItem(newsId: string) {
  return useQuery({ queryKey: newsItemQueryKey(newsId), queryFn: () => fetchNewsItem(newsId) });
}
