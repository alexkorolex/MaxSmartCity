import { CellList, CellSimple } from '@maxhub/max-ui';
import { Link } from 'react-router-dom';

import { useNewsList } from '@/entities/news';
import { ROUTES } from '@/shared/routes';
import { AsyncState, EmptyState, PageLayout } from '@/shared/ui';

function formatDate(iso: string | null): string {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
}

export function NewsPage() {
  const news = useNewsList();

  return (
    <PageLayout title="Новости и события">
      <AsyncState isLoading={news.isLoading} error={news.error} onRetry={() => news.refetch()}>
        {news.data && news.data.length === 0 ? (
          <EmptyState title="Пока новостей нет" description="Загляните позже" />
        ) : (
          <CellList mode="island">
            {news.data?.map((item) => (
              <CellSimple
                key={item.id}
                asChild
                title={item.title}
                subtitle={formatDate(item.published_at)}
                subtitleMode="tertiary"
                showChevron
                separator
              >
                <Link to={ROUTES.newsItem(item.id)} />
              </CellSimple>
            ))}
          </CellList>
        )}
      </AsyncState>
    </PageLayout>
  );
}
