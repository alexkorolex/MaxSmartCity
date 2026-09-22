import { http } from '@/shared/api';

import type { AppNotification } from '../model/types';

export function fetchNotifications(): Promise<AppNotification[]> {
  return http.get<AppNotification[]>('/notifications/');
}

export function markNotificationRead(notificationId: string): Promise<AppNotification> {
  return http.post<AppNotification>(`/notifications/${notificationId}/read`);
}

export function markAllNotificationsRead(): Promise<{ updated: number }> {
  return http.post<{ updated: number }>('/notifications/read-all');
}
