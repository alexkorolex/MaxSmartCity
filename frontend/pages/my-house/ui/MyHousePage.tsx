import { CellList, CellSimple } from '@maxhub/max-ui';
import { Link } from 'react-router-dom';

import { INCIDENT_STATUS_LABELS, INCIDENT_STATUS_TONES, useMyHouseIncidents } from '@/entities/incident';
import { formatCalendarDate } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, EmptyState, HouseIcon, ListCard, PageLayout, StatusBadge } from '@/shared/ui';

function formatDate(iso: string | null): string | undefined {
  if (!iso) return undefined;
  return `Обновлено ${formatCalendarDate(iso)}`;
}

export function MyHousePage() {
  const incidents = useMyHouseIncidents();

  return (
    <PageLayout title="Мой дом" subtitle="Проблемы по вашему адресу" eyebrow="Рядом с вами">
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
