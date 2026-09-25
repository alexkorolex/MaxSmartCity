import { Avatar, CellList, CellSimple, Flex, Typography } from '@maxhub/max-ui';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { useMyHouseIncidents } from '@/entities/incident';
import { useNewsList, type NewsPost } from '@/entities/news';
import { useNotifications, useUnreadNotificationsCount, type AppNotification } from '@/entities/notification';
import { useMyReports } from '@/entities/report';
import { useMyProfile } from '@/entities/user';
import { ROUTES } from '@/shared/routes';
import { HouseIcon, ListCard, PageLayout, PlusIcon, ReportsIcon } from '@/shared/ui';

import './HomePage.css';

function initialsOf(name: string | null | undefined): string {
  if (!name) return '?';
  return name.split(' ').filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join('');
}

interface StatTileProps {
  to: string;
  icon: ReactNode;
  value: number;
  label: string;
}

function StatTile({ to, icon, value, label }: StatTileProps) {
  return (
    <Link to={to} className="surface-card stat-tile">
      <div className="stat-tile__top">
        <span className="stat-tile__icon">{icon}</span>
        <span className="stat-tile__value">{value}</span>
      </div>
      <span className="stat-tile__label">{label}</span>
    </Link>
  );
}

function SectionTitle({ title, to }: { title: string; to: string }) {
  return (
    <div className="section-title">
      <Typography.Text variant="body-strong" color="primary">{title}</Typography.Text>
      <Link className="section-title__link" to={to}>Все</Link>
    </div>
  );
}

function HomeHero({ name, initials }: { name: string; initials: string }) {
  return (
    <section className="home-hero">
      <Flex className="home-hero__top" align="center" justify="space-between" gap="var(--space-3)">
        <div className="home-hero__copy">
          <span className="home-hero__eyebrow">Smart City</span>
          <h1 className="home-hero__title">Здравствуйте, {name}</h1>
          <span className="home-hero__subtitle">Городские вопросы — в одном понятном приложении</span>
        </div>
        <div className="home-hero__avatar">
          <Avatar.Container size={42}>
            <Avatar.Image alt={name} fallback={initials} fallbackGradient="blue" />
          </Avatar.Container>
        </div>
      </Flex>
      <Link className="home-cta" to={ROUTES.reportNew}>
        <span className="home-cta__icon"><PlusIcon width={20} height={20} /></span>
        <span className="home-cta__copy">
          <span className="home-cta__title">Сообщить о проблеме</span>
          <span className="home-cta__hint">Опишите ситуацию — остальное мы подскажем</span>
        </span>
        <span aria-hidden="true">›</span>
      </Link>
    </section>
  );
}

function EventsSection({ items, unreadCount }: { items: AppNotification[]; unreadCount: number }) {
  if (items.length === 0) return null;
  const title = unreadCount > 0 ? 'Новые события · ' + unreadCount : 'Последние события';
  return (
    <section className="app-section">
      <SectionTitle title={title} to={ROUTES.notifications} />
      <ListCard><CellList mode="full-width">
        {items.slice(0, 2).map((item) => (
          <CellSimple key={item.id} asChild title={item.title} subtitle={item.body} subtitleMode="tertiary" showChevron separator>
            <Link to={ROUTES.notifications} />
          </CellSimple>
        ))}
      </CellList></ListCard>
    </section>
  );
}

function NewsSection({ items }: { items: NewsPost[] }) {
  if (items.length === 0) return null;
  return (
    <section className="app-section">
      <SectionTitle title="Новости рядом" to={ROUTES.news} />
      <ListCard><CellList mode="full-width">
        {items.slice(0, 2).map((item) => (
          <CellSimple key={item.id} asChild title={item.title} showChevron separator>
            <Link to={ROUTES.newsItem(item.id)} />
          </CellSimple>
        ))}
      </CellList></ListCard>
    </section>
  );
}

export function HomePage() {
  const profile = useMyProfile();
  const notifications = useNotifications();
  const reports = useMyReports();
  const incidents = useMyHouseIncidents();
  const news = useNewsList();
  const unreadCount = useUnreadNotificationsCount();
  const name = profile.data?.display_name?.split(' ')[0] ?? profile.data?.username ?? 'сосед';

  return (
    <PageLayout>
      <HomeHero name={name} initials={initialsOf(profile.data?.display_name)} />
      <div className="stats-grid">
        <StatTile to={ROUTES.myReports} icon={<ReportsIcon width={18} />} value={reports.data?.length ?? 0} label="Мои обращения" />
        <StatTile to={ROUTES.myHouse} icon={<HouseIcon width={18} />} value={incidents.data?.length ?? 0} label="Проблемы дома" />
      </div>
      <EventsSection items={notifications.data ?? []} unreadCount={unreadCount} />
      <NewsSection items={news.data ?? []} />
    </PageLayout>
  );
}
