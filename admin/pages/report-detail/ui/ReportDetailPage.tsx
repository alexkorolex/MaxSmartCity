import { Link, useParams } from 'react-router-dom';

import {
  PRIORITY_LABELS,
  PRIORITY_TONES,
  REPORT_STATUS_LABELS,
  REPORT_STATUS_TONES,
  useProblemCategories,
  useReport,
  useReportAttachments,
} from '@/entities/report';
import { useResident } from '@/entities/resident';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, Breadcrumbs, ChevronRightIcon, CommentIcon, EmptyState, InboxIcon, Pill } from '@/shared/ui';

import './ReportDetailPage.css';

export function ReportDetailPage() {
  const { reportId = '' } = useParams();
  const report = useReport(reportId);
  const attachments = useReportAttachments(reportId);
  const categories = useProblemCategories();
  const resident = useResident(report.data?.resident_id ?? '');

  const categoryName = report.data?.category_id
    ? categories.data?.find((category) => category.id === report.data?.category_id)?.name
    : undefined;

  return (
    <>
      <Breadcrumbs items={[{ label: 'Сообщения', to: ROUTES.messages }, { label: 'Обращение' }]} />

      <AsyncState isLoading={report.isLoading} error={report.error} onRetry={() => void report.refetch()}>
        {report.data && (
          <div className="card">
            <div className="card__header">
              <div>
                <div className="card__title">{report.data.text ?? 'Без описания'}</div>
                <div className="card__meta">
                  {report.data.resident_id ? (
                    resident.data ? (
                      <Link to={ROUTES.resident(report.data.resident_id)}>
                        {resident.data.display_name ?? 'Житель'}
                      </Link>
                    ) : (
                      'Загрузка жителя…'
                    )
                  ) : (
                    'Автор не указан'
                  )}
                </div>
              </div>
              <div className="detail-badges">
                <Pill tone={REPORT_STATUS_TONES[report.data.status]} label={REPORT_STATUS_LABELS[report.data.status]} />
                <Pill tone={PRIORITY_TONES[report.data.urgency]} label={PRIORITY_LABELS[report.data.urgency]} />
              </div>
            </div>
            <div className="card__body">
              <div className="stat-grid">
                {categoryName && (
                  <div className="stat-card">
                    <div className="stat-card__label">Категория</div>
                    <div className="stat-card__value stat-card__value--compact">
                      {categoryName}
                    </div>
                  </div>
                )}
                <div className="stat-card">
                  <div className="stat-card__label">Принято</div>
                  <div className="stat-card__value stat-card__value--compact">
                    {formatDateTime(report.data.received_at)}
                  </div>
                </div>
                {report.data.occurred_at && (
                  <div className="stat-card">
                    <div className="stat-card__label">Когда произошло</div>
                    <div className="stat-card__value stat-card__value--compact">
                      {formatDateTime(report.data.occurred_at)}
                    </div>
                  </div>
                )}
                {report.data.problem_continues !== null && (
                  <div className="stat-card">
                    <div className="stat-card__label">Проблема продолжается</div>
                    <div className="stat-card__value stat-card__value--compact">
                      {report.data.problem_continues ? 'Да' : 'Нет'}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </AsyncState>

      {report.data?.resident_id && (
        <Link to={ROUTES.reportChat(report.data.id)} className="card report-chat-link">
          <span className="report-chat-link__icon" aria-hidden="true">
            <CommentIcon />
          </span>
          <span className="report-chat-link__copy">
            <span className="card__title">Переписка с жителем</span>
            <span className="card__meta">Вопросы по обращению и ответы жителю — в отдельном чате</span>
          </span>
          <span className="report-chat-link__action">
            <span className="report-chat-link__label">Открыть чат</span>
            <ChevronRightIcon width={16} height={16} />
          </span>
        </Link>
      )}

      <div className="card">
        <div className="card__header">
          <div className="card__title">Фото</div>
        </div>
        <div className="card__body">
          <AsyncState
            isLoading={attachments.isLoading}
            error={attachments.error}
            onRetry={() => void attachments.refetch()}
          >
            {!attachments.data || attachments.data.length === 0 ? (
              <EmptyState icon={<InboxIcon />} title="Фото не приложено" />
            ) : (
              <div className="attachment-grid">
                {attachments.data.map((attachment) => (
                  <a
                    key={attachment.id}
                    className="attachment-thumb"
                    href={attachment.download_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <img src={attachment.download_url} alt={attachment.original_name ?? ''} />
                  </a>
                ))}
              </div>
            )}
          </AsyncState>
        </div>
      </div>
    </>
  );
}
