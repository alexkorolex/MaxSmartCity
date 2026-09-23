import { http } from '@/shared/api';

import type { NewsPost } from '../model/types';

export function fetchNews(): Promise<NewsPost[]> {
  return http.get<NewsPost[]>('/news/', { query: { limit: 50 } });
}

export function fetchNewsItem(newsId: string): Promise<NewsPost> {
  return http.get<NewsPost>(`/news/${newsId}`);
}
