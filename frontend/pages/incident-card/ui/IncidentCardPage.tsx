import { Button, CellHeader, CellList, CellSimple, Typography } from '@maxhub/max-ui';
import { Link, useParams } from 'react-router-dom';

import { canConfirmOrDispute, INCIDENT_STATUS_LABELS, useIncident } from '@/entities/incident';
import { ROUTES } from '@/shared/routes';
import { AsyncState, PageLayout } from '@/shared/ui';

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}

export function IncidentCardPage() {
  const { incidentId = '' } = useParams<{ incidentId: string }>();
  const incident = useIncident(incidentId);

  return (
    <PageLayout title="Карточка инцидента">
      <AsyncState isLoading={incident.isLoading} error={incident.error} onRetry={() => incident.refetch()}>
        {incident.data && (
          <>
            <Typography.Text variant="title" color="primary">
              {incident.data.title}
            </Typography.Text>
            {incident.data.description && (
              <Typography.Text variant="body" color="secondary">
                {incident.data.description}
              </Typography.Text>
            )}

            <CellList mode="island" header={<CellHeader>Статус</CellHeader>}>
              <CellSimple title="Статус" subtitle={INCIDENT_STATUS_LABELS[incident.data.status]} subtitleMode="tertiary" />
              <CellSimple title="Первое обращение" subtitle={formatDate(incident.data.first_report_at)} subtitleMode="tertiary" />
              <CellSimple title="Ожидаемый срок решения" subtitle={formatDate(incident.data.expected_resolution_at)} subtitleMode="tertiary" />
              {incident.data.resolved_at && (
                <CellSimple title="Решено" subtitle={formatDate(incident.data.resolved_at)} subtitleMode="tertiary" />
              )}
            </CellList>

            {canConfirmOrDispute(incident.data.status) && (
              <Button asChild variant="primary" size="large" stretched>
                <Link to={ROUTES.incidentResolution(incident.data.id)}>Подтвердить или оспорить решение</Link>
              </Button>
            )}
          </>
        )}
      </AsyncState>
    </PageLayout>
  );
}
