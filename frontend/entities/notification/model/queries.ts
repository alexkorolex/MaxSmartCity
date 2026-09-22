import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { fetchNotifications, markAllNotificationsRead, markNotificationRead } from '../api/notifications';

export const notificationsQueryKey = ['notifications'] as const;

export function useNotifications() {
  return useQuery({ queryKey: notificationsQueryKey, queryFn: fetchNotifications });
}

export function useUnreadNotificationsCount(): number {
  const { data } = useNotifications();
  return data?.filter((notification) => !notification.is_read).length ?? 0;
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) => markNotificationRead(notificationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: notificationsQueryKey });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => markAllNotificationsRead(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: notificationsQueryKey });
    },
  });
}
