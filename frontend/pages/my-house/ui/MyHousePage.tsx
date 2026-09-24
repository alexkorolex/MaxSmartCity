import { Button, CellList, CellSimple, Flex, Typography } from '@maxhub/max-ui';
import { Link } from 'react-router-dom';

import { useHouseInfo } from '@/entities/geo';
import { INCIDENT_STATUS_LABELS, INCIDENT_STATUS_TONES, useMyHouseIncidents } from '@/entities/incident';
import { useMyProfile } from '@/entities/user';
import { formatCalendarDate } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, EmptyState, HouseIcon, ListCard, PageLayout, StatusBadge } from '@/shared/ui';
import { HouseInfoSection } from '@/widgets/house-info';

function formatDate(iso: string | null): string | undefined {
  if (!iso) return undefined;
  return `Обновлено ${formatCalendarDate(iso)}`;
}

function MyHouseAddress({ houseId }: { houseId: string }) {
  const info = useHouseInfo(houseId);
  if (!info.data) return null;
  return (
    <Flex direction="column" gap="var(--space-1)" className="surface-card detail-hero">
      <Typography.Text variant="title" color="primary">
        {[info.data.house.street, info.data.house.house_number].filter(Boolean).join(', ') || info.data.house.formatted}
      </Typography.Text>
      <Typography.Text variant="description" color="secondary">
        {info.data.house.formatted}
      </Typography.Text>
      <Link to={ROUTES.selectHouse} className="section-title__link">
        Изменить адрес
      </Link>
    </Flex>
  );
}

export function MyHousePage() {
  const incidents = useMyHouseIncidents();
  const profile = useMyProfile();
  const houseId = profile.data?.house_id ?? null;

  return (
    <PageLayout title="Мой дом" subtitle="Управляющая компания и проблемы по вашему адресу" eyebrow="Рядом с вами">
      {houseId ? (
        <>
          <MyHouseAddress houseId={houseId} />
          <HouseInfoSection houseId={houseId} />
        </>
      ) : (
        profile.data && (
          <Flex direction="column" gap="var(--space-3)" className="surface-card detail-hero">
            <Typography.Text variant="body-strong" color="primary">
              Укажите свой дом
            </Typography.Text>
            <Typography.Text variant="description" color="secondary">
              Мы покажем, какая управляющая компания его обслуживает, её телефоны и сайт.
            </Typography.Text>
            <Button asChild variant="primary" size="medium" stretched>
              <Link to={ROUTES.selectHouse}>Выбрать дом</Link>
            </Button>
          </Flex>
        )
      )}

      <div className="section-title">
        <Typography.Text variant="body-strong" color="primary">
          Проблемы по дому
        </Typography.Text>
      </div>
      <AsyncState isLoading={incidents.isLoading} error={incidents.error} onRetry={() => incidents.refetch()}>
        {incidents.data && incidents.data.length === 0 ? (
          <EmptyState
            icon={<HouseIcon width={28} height={28} />}
            title="Проблем не найдено"
            description="Мы определяем ваш дом по адресу из последнего обращения. Если вы ещё не сообщали о проблеме, отправьте обращение — и мы сможем показать проблемы вашего дома."
          />
        ) : (
          <ListCard>
          <CellList mode="full-width">
            {incidents.data?.map((incident) => (
              <CellSimple
                key={incident.id}
                asChild
                title={incident.title}
                subtitle={formatDate(incident.last_report_at)}
                subtitleMode="tertiary"
                overline={<StatusBadge label={INCIDENT_STATUS_LABELS[incident.status]} tone={INCIDENT_STATUS_TONES[incident.status]} />}
                showChevron
                separator
              >
                <Link to={ROUTES.incident(incident.id)} />
              </CellSimple>
            ))}
          </CellList>
          </ListCard>
        )}
      </AsyncState>
    </PageLayout>
  );
}
