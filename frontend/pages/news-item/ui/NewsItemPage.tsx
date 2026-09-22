import { Typography } from '@maxhub/max-ui';
import { useParams } from 'react-router-dom';

import { useNewsItem } from '@/entities/news';
import { AsyncState, PageLayout } from '@/shared/ui';

function formatDate(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}

export function NewsItemPage() {
  const { newsId = '' } = useParams<{ newsId: string }>();
  const news = useNewsItem(newsId);

  return (
    <PageLayout title="Новость">
      <AsyncState isLoading={news.isLoading} error={news.error} onRetry={() => news.refetch()}>
        {news.data && (
          <>
            <Typography.Text variant="title" color="primary">
              {news.data.title}
            </Typography.Text>
            <Typography.Text variant="detail" color="secondary">
              {formatDate(news.data.published_at)}
            </Typography.Text>
            <Typography.Text variant="body" color="primary">
              {news.data.body}
            </Typography.Text>
          </>
        )}
      </AsyncState>
    </PageLayout>
  );
}
