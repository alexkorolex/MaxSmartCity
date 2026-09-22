import { Button, CellList, CellSimple } from '@maxhub/max-ui';
import { Link } from 'react-router-dom';

import { REPORT_STATUS_LABELS, useMyReports } from '@/entities/report';
import { ROUTES } from '@/shared/routes';
import { AsyncState, EmptyState, PageLayout } from '@/shared/ui';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}

export function MyReportsPage() {
  const reports = useMyReports();

  return (
    <PageLayout title="Мои обращения">
      <AsyncState isLoading={reports.isLoading} error={reports.error} onRetry={() => reports.refetch()}>
        {reports.data && reports.data.length === 0 ? (
          <EmptyState
            title="Пока нет обращений"
            description="Сообщите о первой проблеме — это займёт меньше минуты."
            action={
              <Button asChild variant="primary">
                <Link to={ROUTES.reportNew}>Сообщить о проблеме</Link>
              </Button>
            }
          />
        ) : (
          <CellList mode="island">
            {reports.data?.map((report) => (
              <CellSimple
                key={report.id}
                title={report.text ?? 'Без описания'}
                subtitle={`${REPORT_STATUS_LABELS[report.status]} · ${formatDate(report.received_at)}`}
                subtitleMode="tertiary"
                separator
              />
            ))}
          </CellList>
        )}
      </AsyncState>
    </PageLayout>
  );
}
