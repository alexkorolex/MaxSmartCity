import { CellList, CellSimple } from '@maxhub/max-ui';
import { Link } from 'react-router-dom';

import { useNewsList } from '@/entities/news';
import { formatCalendarDate } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, EmptyState, ListCard, NewsIcon, PageLayout } from '@/shared/ui';

export function NewsPage() {
  const news = useNewsList();

  return (
    <PageLayout title="Новости" subtitle="Важное о городе и вашем районе" eyebrow="Город рядом">
      <AsyncState isLoading={news.isLoading} error={news.error} onRetry={() => news.refetch()}>
        {news.data && news.data.length === 0 ? (
          <EmptyState icon={<NewsIcon width={28} height={28} />} title="Пока новостей нет" description="Загляните позже" />
        ) : (
          <ListCard>
          <CellList mode="full-width">
            {news.data?.map((item) => (
              <CellSimple
                key={item.id}
                asChild
                title={item.title}
                subtitle={formatCalendarDate(item.published_at)}
                subtitleMode="tertiary"
                showChevron
                separator
              >
                <Link to={ROUTES.newsItem(item.id)} />
              </CellSimple>
            ))}
          </CellList>
          </ListCard>
        )}
      </AsyncState>
    </PageLayout>
  );
}
