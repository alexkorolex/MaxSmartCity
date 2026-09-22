import { Button, CellHeader, CellList, CellSimple, Flex, Typography } from '@maxhub/max-ui';
import { Link } from 'react-router-dom';

import { useNewsList } from '@/entities/news';
import { useNotifications } from '@/entities/notification';
import { useMyProfile } from '@/entities/user';
import { ROUTES } from '@/shared/routes';
import { PageLayout } from '@/shared/ui';

export function HomePage() {
  const profile = useMyProfile();
  const notifications = useNotifications();
  const news = useNewsList();

  const greetingName = profile.data?.display_name ?? profile.data?.username ?? 'сосед';
  const recentNotifications = notifications.data?.slice(0, 3) ?? [];
  const recentNews = news.data?.slice(0, 2) ?? [];

  return (
    <PageLayout>
      <Flex direction="column" gap={4}>
        <Typography.Text variant="header" color="primary">
          Здравствуйте, {greetingName}!
        </Typography.Text>
        <Typography.Text variant="description" color="secondary">
          Max Smart City — сообщайте о городских проблемах и следите за их решением.
        </Typography.Text>
      </Flex>

      <Flex direction="column" gap={8}>
        <Button asChild variant="primary" size="large" stretched>
          <Link to={ROUTES.reportNew}>Сообщить о проблеме</Link>
        </Button>
        <Button asChild variant="secondary" size="large" stretched>
          <Link to={ROUTES.myHouse}>Проблемы моего дома</Link>
        </Button>
      </Flex>

      {recentNotifications.length > 0 && (
        <CellList
          mode="island"
          header={<CellHeader>Последние уведомления</CellHeader>}
        >
          {recentNotifications.map((notification) => (
            <CellSimple
              key={notification.id}
              asChild
              title={notification.title}
              subtitle={notification.body}
              subtitleMode="tertiary"
              showChevron
            >
              <Link to={ROUTES.notifications} />
            </CellSimple>
          ))}
        </CellList>
      )}

      {recentNews.length > 0 && (
        <CellList mode="island" header={<CellHeader>Новости и события</CellHeader>}>
          {recentNews.map((item) => (
            <CellSimple key={item.id} asChild title={item.title} showChevron>
              <Link to={ROUTES.newsItem(item.id)} />
            </CellSimple>
          ))}
        </CellList>
      )}
    </PageLayout>
  );
}
