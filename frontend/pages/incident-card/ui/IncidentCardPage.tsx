import { Button, CellHeader, CellList, CellSimple, Flex, Typography } from '@maxhub/max-ui';
import { Link, useParams } from 'react-router-dom';

import {
  canConfirmOrDispute,
  INCIDENT_STATUS_LABELS,
  INCIDENT_STATUS_TONES,
  useIncident,
  useMyIncidentReport,
} from '@/entities/incident';
import { PRIORITY_LABELS, PRIORITY_TONES } from '@/entities/report';
import { ROUTES } from '@/shared/routes';
import { formatCalendarDate } from '@/shared/lib';
import { AsyncState, ListCard, PageLayout, StatusBadge } from '@/shared/ui';

import './IncidentCardPage.css';

export function IncidentCardPage() {
  const { incidentId = '' } = useParams<{ incidentId: string }>();
  const incident = useIncident(incidentId);
  const myReport = useMyIncidentReport(incidentId);

  return (
    <PageLayout title="Инцидент" subtitle="Подробности и текущий статус" backTo={ROUTES.myHouse} backLabel="Мой дом" withNavSpacing={false}>
      <AsyncState isLoading={incident.isLoading} error={incident.error} onRetry={() => incident.refetch()}>
        {incident.data && (
          <>
            <Flex
              direction="column"
              gap="var(--space-3)"
              className="surface-card detail-hero"
            >
              <Flex gap="var(--space-2)" wrap="wrap">
                <StatusBadge
                  label={INCIDENT_STATUS_LABELS[incident.data.status]}
                  tone={INCIDENT_STATUS_TONES[incident.data.status]}
                />
                <StatusBadge
                  label={PRIORITY_LABELS[incident.data.priority]}
                  tone={PRIORITY_TONES[incident.data.priority]}
                />
              </Flex>
              <Typography.Text variant="title" color="primary">
                {incident.data.title}
              </Typography.Text>
              {incident.data.description && (
                <Typography.Text variant="body" color="secondary">
                  {incident.data.description}
                </Typography.Text>
              )}
            </Flex>

            <ListCard>
            <CellList mode="full-width" header={<CellHeader>Сроки</CellHeader>}>
              <CellSimple title="Первое обращение" subtitle={formatCalendarDate(incident.data.first_report_at, { year: true, fallback: '—' })} subtitleMode="tertiary" />
              <CellSimple title="Ожидаемый срок решения" subtitle={formatCalendarDate(incident.data.expected_resolution_at, { year: true, fallback: '—' })} subtitleMode="tertiary" />
              {incident.data.resolved_at && (
                <CellSimple title="Решено" subtitle={formatCalendarDate(incident.data.resolved_at, { year: true })} subtitleMode="tertiary" />
              )}
            </CellList>
            </ListCard>

            {canConfirmOrDispute(incident.data.status) && myReport.data && !myReport.data.has_open_dispute && (
              <Flex
                direction="column"
                gap="var(--space-3)"
                className="surface-card incident-resolution-callout"
              >
                <Typography.Text variant="body-strong" color="primary">
                  Проблема отмечена как решённая
                </Typography.Text>
                <Typography.Text variant="description" color="secondary">
                  Подтвердите, что всё в порядке, или сообщите, если проблема осталась.
                </Typography.Text>
                <Button asChild variant="primary" size="large" stretched>
                  <Link to={ROUTES.incidentResolution(incident.data.id)}>Проверить решение</Link>
                </Button>
              </Flex>
            )}
          </>
        )}
      </AsyncState>
    </PageLayout>
  );
}
