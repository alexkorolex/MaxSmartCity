import { Button, Flex, Typography } from '@maxhub/max-ui';

import { useDecideReportGrouping, useReportGrouping } from '@/entities/report';
import { AsyncState } from '@/shared/ui';

import './ClarifyReportCard.css';

export function ClarifyReportCard({ reportId }: { reportId: string }) {
  const grouping = useReportGrouping(reportId, true);
  const decision = useDecideReportGrouping(reportId);

  return (
    <Flex direction="column" gap="var(--space-3)" className="surface-card clarify-report">
      <div className="clarify-report__heading">
        <Typography.Text variant="body-strong" color="primary">
          Уточните, к какой проблеме относится обращение
        </Typography.Text>
        <Typography.Text variant="description" color="secondary">
          Возможно, соседи уже сообщили о том же. Выберите похожую проблему дома или создайте отдельную.
        </Typography.Text>
      </div>
      <AsyncState isLoading={grouping.isLoading} error={grouping.error} onRetry={() => grouping.refetch()}>
        {grouping.data && (
          <>
            <ul className="clarify-report__options">
              {grouping.data.candidate_incident_ids.map((incidentId, index) => {
                const incident = grouping.data.candidate_incidents.find((item) => item.incident_id === incidentId);
                return (
                  <li key={incidentId}>
                    <button
                      type="button"
                      className="clarify-report__option"
                      disabled={decision.isPending}
                      onClick={() => decision.mutate({ mode: 'CONFIRM_INCIDENT', confirmed_incident_id: incidentId })}
                    >
                      <span className="clarify-report__number" aria-hidden="true">
                        {index + 1}
                      </span>
                      <span className="clarify-report__text">
                        <span className="clarify-report__title">{incident?.title ?? 'Похожая проблема дома'}</span>
                        {incident?.description && (
                          <span className="clarify-report__description">{incident.description}</span>
                        )}
                      </span>
                      <svg className="clarify-report__chevron" viewBox="0 0 24 24" aria-hidden="true">
                        <path d="m9 6 6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </button>
                  </li>
                );
              })}
            </ul>
            <Button
              variant="secondary"
              size="large"
              stretched
              disabled={decision.isPending}
              onClick={() => decision.mutate({ mode: 'FORCE_NEW' })}
            >
              Это другая проблема
            </Button>
          </>
        )}
      </AsyncState>
      {decision.isError && (
        <Typography.Text variant="description" className="clarify-report__error">
          Не удалось сохранить выбор. Обновите страницу и попробуйте ещё раз.
        </Typography.Text>
      )}
    </Flex>
  );
}
