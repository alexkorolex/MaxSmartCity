import { Button, CellList, CellSimple } from '@maxhub/max-ui';
import { Link } from 'react-router-dom';

import type { AppNotification } from '@/entities/notification';
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from '@/entities/notification';
import { ROUTES } from '@/shared/routes';
import { formatDateTime } from '@/shared/lib';
import { AsyncState, BellIcon, EmptyState, ListCard, PageLayout } from '@/shared/ui';

function NotificationRow({ notification }: { notification: AppNotification }) {
  const markRead = useMarkNotificationRead();
  const target = notification.incident_id ? ROUTES.incident(notification.incident_id) : undefined;

  const cellProps = {
    title: notification.title,
    subtitle: `${notification.body} · ${formatDateTime(notification.created_at)}`,
    subtitleMode: 'tertiary' as const,
    separator: true,
    before: !notification.is_read ? (
      <span
        style={{
          display: 'block',
          width: 9,
          height: 9,
          borderRadius: 'var(--radius-full)',
          background: 'var(--blue)',
        }}
      />
    ) : undefined,
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
      subtitle="Изменения по вашим обращениям"
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
          <EmptyState
            icon={<BellIcon width={28} height={28} />}
            title="Уведомлений нет"
            description="Здесь будут появляться обновления по вашим обращениям"
          />
        ) : (
          <ListCard>
          <CellList mode="full-width">
            {notifications.data?.map((notification) => (
              <NotificationRow key={notification.id} notification={notification} />
            ))}
          </CellList>
          </ListCard>
        )}
      </AsyncState>
    </PageLayout>
  );
}
