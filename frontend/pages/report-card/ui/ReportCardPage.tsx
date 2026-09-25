import { CellHeader, CellList, CellSimple, Flex, Typography } from '@maxhub/max-ui';
import { useParams } from 'react-router-dom';

import {
  PRIORITY_LABELS,
  PRIORITY_TONES,
  REPORT_STATUS_LABELS,
  REPORT_STATUS_TONES,
  useProblemCategories,
  useReport,
  useReportAttachments,
} from '@/entities/report';
import { CloseReportCard } from '@/features/close-report';
import { ReportChat } from '@/features/report-chat';
import { formatCalendarDate, formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, ListCard, PageLayout, StatusBadge } from '@/shared/ui';

import './ReportCardPage.css';

export function ReportCardPage() {
  const { reportId = '' } = useParams<{ reportId: string }>();
  const report = useReport(reportId);
  const attachments = useReportAttachments(reportId);
  const categories = useProblemCategories();

  const categoryName = report.data?.category_id
    ? categories.data?.find((category) => category.id === report.data?.category_id)?.name
    : undefined;

  return (
    <PageLayout
      title="Обращение"
      subtitle="Подробности вашего обращения"
      backTo={ROUTES.myReports}
      withNavSpacing={false}
    >
      <AsyncState isLoading={report.isLoading} error={report.error} onRetry={() => report.refetch()}>
        {report.data && (
          <>
            <Flex direction="column" gap="var(--space-3)" className="surface-card detail-hero">
              <Flex gap="var(--space-2)" wrap="wrap">
                <StatusBadge
                  label={REPORT_STATUS_LABELS[report.data.status]}
                  tone={REPORT_STATUS_TONES[report.data.status]}
                />
                <StatusBadge
                  label={PRIORITY_LABELS[report.data.urgency]}
                  tone={PRIORITY_TONES[report.data.urgency]}
                />
              </Flex>
              <Typography.Text variant="body" color="primary">
                {report.data.text ?? 'Без описания'}
              </Typography.Text>
            </Flex>

            <ListCard>
              <CellList mode="full-width" header={<CellHeader>Детали</CellHeader>}>
                {categoryName && (
                  <CellSimple title="Категория" subtitle={categoryName} subtitleMode="tertiary" />
                )}
                <CellSimple
                  title="Принято"
                  subtitle={formatDateTime(report.data.received_at)}
                  subtitleMode="tertiary"
                />
                {report.data.occurred_at && (
                  <CellSimple
                    title="Когда произошло"
                    subtitle={formatCalendarDate(report.data.occurred_at, { year: true })}
                    subtitleMode="tertiary"
                  />
                )}
                {report.data.problem_continues !== null && (
                  <CellSimple
                    title="Проблема продолжается"
                    subtitle={report.data.problem_continues ? 'Да' : 'Нет'}
                    subtitleMode="tertiary"
                  />
                )}
              </CellList>
            </ListCard>

            <ReportChat reportId={report.data.id} />

            <CloseReportCard report={report.data} />

            {(attachments.isLoading || (attachments.data && attachments.data.length > 0)) && (
              <ListCard>
                <CellList mode="full-width" header={<CellHeader>Фото</CellHeader>}>
                  <AsyncState
                    isLoading={attachments.isLoading}
                    error={attachments.error}
                    onRetry={() => attachments.refetch()}
                  >
                    <div className="report-attachments">
                      {attachments.data?.map((attachment) => (
                        <a
                          key={attachment.id}
                          className="report-attachments__item"
                          href={attachment.download_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <img src={attachment.download_url} alt={attachment.original_name ?? ''} />
                        </a>
                      ))}
                    </div>
                  </AsyncState>
                </CellList>
              </ListCard>
            )}
          </>
        )}
      </AsyncState>
    </PageLayout>
  );
}
