import { http } from '@/shared/api';

import type { NewsPost, NewsPostCreatePayload, NewsPostUpdatePayload } from '../model/types';

export function fetchNews(): Promise<NewsPost[]> {
  return http.get<NewsPost[]>('/news/', { query: { limit: 100 } });
}

export function fetchNewsItem(newsId: string): Promise<NewsPost> {
  return http.get<NewsPost>(`/news/${newsId}`);
}

export function createNewsItem(payload: NewsPostCreatePayload): Promise<NewsPost> {
  return http.post<NewsPost>('/news/', payload);
}

export function updateNewsItem(newsId: string, payload: NewsPostUpdatePayload): Promise<NewsPost> {
  return http.patch<NewsPost>(`/news/${newsId}`, payload);
}

export function deleteNewsItem(newsId: string): Promise<void> {
  return http.delete(`/news/${newsId}`);
}
