import { Button, Flex, Typography } from '@maxhub/max-ui';

import { useDecideReportGrouping, useReportGrouping } from '@/entities/report';
import { formatCalendarDate } from '@/shared/lib';
import { AsyncState } from '@/shared/ui';

import './ClarifyReportCard.css';

function residentsLabel(count: number): string {
  const lastTwo = count % 100;
  const last = count % 10;
  if (lastTwo >= 11 && lastTwo <= 14) return `${count} жителей`;
  if (last === 1) return `${count} житель`;
  if (last >= 2 && last <= 4) return `${count} жителя`;
  return `${count} жителей`;
}

function reportedLabel(count: number, since: string | null): string {
  const who = count > 0 ? `Уже сообщили ${residentsLabel(count)}` : 'Уже в работе';
  const when = formatCalendarDate(since);
  return when ? `${who} · с ${when}` : who;
}

export function ClarifyReportCard({ reportId }: { reportId: string }) {
  const grouping = useReportGrouping(reportId, true);
  const decision = useDecideReportGrouping(reportId);

  return (
    <Flex direction="column" gap="var(--space-4)" className="surface-card clarify-report">
      <div className="clarify-report__heading">
        <Typography.Text variant="body-strong" color="primary">
          Похоже, об этом уже сообщали соседи
        </Typography.Text>
        <Typography.Text variant="description" color="secondary">
          Если это та же проблема, ваше обращение присоединится к ней — вы будете получать новости о ходе работ, а
          исполнитель увидит, что проблема касается многих.
        </Typography.Text>
      </div>
      <AsyncState isLoading={grouping.isLoading} error={grouping.error} onRetry={() => grouping.refetch()}>
        {grouping.data && (
          <>
            <ul className="clarify-report__options">
              {grouping.data.candidate_incident_ids.map((incidentId) => {
                const incident = grouping.data.candidate_incidents.find((item) => item.incident_id === incidentId);
                const headline = incident?.headline ?? incident?.title ?? 'Похожая проблема в доме';
                return (
                  <li key={incidentId}>
                    <button
                      type="button"
                      className="clarify-report__option"
                      disabled={decision.isPending}
                      onClick={() => decision.mutate({ mode: 'CONFIRM_INCIDENT', confirmed_incident_id: incidentId })}
                    >
                      <span className="clarify-report__text">
                        {incident?.category_name && (
                          <span className="clarify-report__category">{incident.category_name}</span>
                        )}
                        <span className="clarify-report__title">{headline}</span>
                        <span className="clarify-report__meta">
                          {reportedLabel(incident?.reports_count ?? 0, incident?.first_report_at ?? null)}
                        </span>
                      </span>
                      <span className="clarify-report__action">
                        Да, это та же проблема
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path
                            d="m9 6 6 6-6 6"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
            <div className="clarify-report__new">
              <Button
                variant="secondary"
                size="large"
                stretched
                disabled={decision.isPending}
                onClick={() => decision.mutate({ mode: 'FORCE_NEW' })}
              >
                Нет, у меня другая проблема
              </Button>
              <Typography.Text variant="description" color="secondary">
                Мы заведём отдельную проблему, и ваше обращение не потеряется.
              </Typography.Text>
            </div>
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
