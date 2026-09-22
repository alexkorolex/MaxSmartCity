import { Button, CellList, CellSimple } from '@maxhub/max-ui';
import { Link } from 'react-router-dom';

import type { AppNotification } from '@/entities/notification';
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from '@/entities/notification';
import { ROUTES } from '@/shared/routes';
import { AsyncState, EmptyState, PageLayout } from '@/shared/ui';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function NotificationRow({ notification }: { notification: AppNotification }) {
  const markRead = useMarkNotificationRead();
  const target = notification.incident_id ? ROUTES.incident(notification.incident_id) : undefined;

  const cellProps = {
    title: notification.title,
    subtitle: `${notification.body} · ${formatDate(notification.created_at)}`,
    subtitleMode: 'tertiary' as const,
    separator: true,
    before: !notification.is_read ? <span style={{ color: 'var(--blue)', fontSize: 20, lineHeight: 1 }}>●</span> : undefined,
    onClick: () => {
      if (!notification.is_read) markRead.mutate(notification.id);
    },
  };

  if (target) {
    return (
      <CellSimple {...cellProps} asChild showChevron>
        <Link to={target} />
      </CellSimple>
    );
  }

  return <CellSimple {...cellProps} />;
}

export function NotificationsPage() {
  const notifications = useNotifications();
  const markAllRead = useMarkAllNotificationsRead();
  const hasUnread = notifications.data?.some((notification) => !notification.is_read) ?? false;

  return (
    <PageLayout
      title="Уведомления"
      action={
        hasUnread ? (
          <Button variant="ghost" size="small" onClick={() => markAllRead.mutate()} loading={markAllRead.isPending}>
            Прочитать всё
          </Button>
        ) : undefined
      }
    >
      <AsyncState isLoading={notifications.isLoading} error={notifications.error} onRetry={() => notifications.refetch()}>
        {notifications.data && notifications.data.length === 0 ? (
          <EmptyState title="Уведомлений нет" description="Здесь будут появляться обновления по вашим обращениям" />
        ) : (
          <CellList mode="island">
            {notifications.data?.map((notification) => (
              <NotificationRow key={notification.id} notification={notification} />
            ))}
          </CellList>
        )}
      </AsyncState>
    </PageLayout>
  );
}
