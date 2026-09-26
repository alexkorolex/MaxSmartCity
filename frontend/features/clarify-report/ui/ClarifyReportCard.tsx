import { Button, Flex, Typography } from '@maxhub/max-ui';

import { useDecideReportGrouping, useReportGrouping } from '@/entities/report';
import { AsyncState } from '@/shared/ui';

export function ClarifyReportCard({ reportId }: { reportId: string }) {
  const grouping = useReportGrouping(reportId, true);
  const decision = useDecideReportGrouping(reportId);

  return (
    <Flex direction="column" gap="var(--space-3)" className="surface-card">
      <Typography.Text variant="body-strong" color="primary">
        Уточните, к какой проблеме относится обращение
      </Typography.Text>
      <Typography.Text variant="description" color="secondary">
        Выберите похожую проблему дома или создайте отдельную.
      </Typography.Text>
      <AsyncState isLoading={grouping.isLoading} error={grouping.error} onRetry={() => grouping.refetch()}>
        {grouping.data?.candidate_incident_ids.map((incidentId, index) => {
          const incident = grouping.data.candidate_incidents.find((item) => item.incident_id === incidentId);
          return (
            <Button
              key={incidentId}
              variant="secondary"
              size="large"
              stretched
              disabled={decision.isPending}
              onClick={() => decision.mutate({ mode: 'CONFIRM_INCIDENT', confirmed_incident_id: incidentId })}
            >
              {`${index + 1}. ${incident?.title ?? 'Похожая проблема дома'}${incident?.description ? ` — ${incident.description.slice(0, 100)}` : ''}`}
            </Button>
          );
        })}
        {grouping.data && (
          <Button
            variant="primary"
            size="large"
            stretched
            disabled={decision.isPending}
            onClick={() => decision.mutate({ mode: 'FORCE_NEW' })}
          >
            Создать отдельную проблему
          </Button>
        )}
      </AsyncState>
      {decision.isError && (
        <Typography.Text variant="description" color="primary">
          Не удалось сохранить выбор. Обновите страницу и попробуйте ещё раз.
        </Typography.Text>
      )}
    </Flex>
  );
}
