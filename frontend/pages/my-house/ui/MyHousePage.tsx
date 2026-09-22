import { CellList, CellSimple } from '@maxhub/max-ui';
import { Link } from 'react-router-dom';

import { INCIDENT_STATUS_LABELS, useMyHouseIncidents } from '@/entities/incident';
import { ROUTES } from '@/shared/routes';
import { AsyncState, EmptyState, PageLayout } from '@/shared/ui';

export function MyHousePage() {
  const incidents = useMyHouseIncidents();

  return (
    <PageLayout title="Проблемы моего дома">
      <AsyncState isLoading={incidents.isLoading} error={incidents.error} onRetry={() => incidents.refetch()}>
        {incidents.data && incidents.data.length === 0 ? (
          <EmptyState
            title="Проблем не найдено"
            description="Мы определяем ваш дом по адресу из последнего обращения. Если вы ещё не сообщали о проблеме, отправьте обращение — и мы сможем показать проблемы вашего дома."
          />
        ) : (
          <CellList mode="island">
            {incidents.data?.map((incident) => (
              <CellSimple
                key={incident.id}
                asChild
                title={incident.title}
                subtitle={INCIDENT_STATUS_LABELS[incident.status]}
                subtitleMode="tertiary"
                showChevron
                separator
              >
                <Link to={ROUTES.incident(incident.id)} />
              </CellSimple>
            ))}
          </CellList>
        )}
      </AsyncState>
    </PageLayout>
  );
}
