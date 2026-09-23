import { Flex, Typography } from '@maxhub/max-ui';
import { useParams } from 'react-router-dom';

import { useNewsItem } from '@/entities/news';
import { formatCalendarDate } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, PageLayout } from '@/shared/ui';

export function NewsItemPage() {
  const { newsId = '' } = useParams<{ newsId: string }>();
  const news = useNewsItem(newsId);

  return (
    <PageLayout title="Новость" backTo={ROUTES.news} withNavSpacing={false}>
      <AsyncState isLoading={news.isLoading} error={news.error} onRetry={() => news.refetch()}>
        {news.data && (
          <Flex className="surface-card reading-card" direction="column" gap="var(--space-2)">
            <Typography.Text variant="detail-strong" color="secondary" style={{ textTransform: 'uppercase', letterSpacing: 0.3 }}>
              {formatCalendarDate(news.data.published_at, { year: true })}
            </Typography.Text>
            <Typography.Text variant="title" color="primary">
              {news.data.title}
            </Typography.Text>
            <Typography.Text className="reading-card__body" variant="body" color="primary" style={{ marginTop: 'var(--space-2)', lineHeight: 1.6 }}>
              {news.data.body}
            </Typography.Text>
          </Flex>
        )}
      </AsyncState>
    </PageLayout>
  );
}
