import { Button, CellList, CellSimple } from '@maxhub/max-ui';
import { Link } from 'react-router-dom';

import { REPORT_STATUS_LABELS, REPORT_STATUS_TONES, useMyReports } from '@/entities/report';
import { formatCalendarDate } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, EmptyState, InboxIcon, ListCard, PageLayout, StatusBadge } from '@/shared/ui';

function reportCountLabel(count: number): string {
  const mod100 = count % 100;
  const mod10 = count % 10;
  if (mod100 >= 11 && mod100 <= 14) return `${count} обращений`;
  if (mod10 === 1) return `${count} обращение`;
  if (mod10 >= 2 && mod10 <= 4) return `${count} обращения`;
  return `${count} обращений`;
}

export function MyReportsPage() {
  const reports = useMyReports();
  const count = reports.data?.length ?? 0;

  return (
    <PageLayout
      title="Обращения"
      subtitle={count > 0 ? reportCountLabel(count) : 'История ваших сообщений городу'}
      eyebrow="На контроле"
    >
      <AsyncState isLoading={reports.isLoading} error={reports.error} onRetry={() => reports.refetch()}>
        {reports.data && reports.data.length === 0 ? (
          <EmptyState
            icon={<InboxIcon width={28} height={28} />}
            title="Пока нет обращений"
            description="Сообщите о первой проблеме — это займёт меньше минуты."
            action={
              <Button asChild variant="primary">
                <Link to={ROUTES.reportNew}>Сообщить о проблеме</Link>
              </Button>
            }
          />
        ) : (
          <ListCard>
            <CellList mode="full-width">
              {reports.data?.map((report) => (
                <CellSimple
                  key={report.id}
                  asChild
                  title={report.text ?? 'Без описания'}
                  subtitle={formatCalendarDate(report.received_at, { year: true })}
                  subtitleMode="tertiary"
                  overline={<StatusBadge label={REPORT_STATUS_LABELS[report.status]} tone={REPORT_STATUS_TONES[report.status]} />}
                  showChevron
                  separator
                >
                  <Link to={ROUTES.report(report.id)} />
                </CellSimple>
              ))}
            </CellList>
          </ListCard>
        )}
      </AsyncState>
    </PageLayout>
  );
}
