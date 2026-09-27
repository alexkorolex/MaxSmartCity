import { useNavigate, useParams } from 'react-router-dom';

import {
  PRIORITY_LABELS,
  PRIORITY_TONES,
  REPORT_STATUS_LABELS,
  REPORT_STATUS_TONES,
  useReports,
} from '@/entities/report';
import { useResident } from '@/entities/resident';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, Breadcrumbs, EmptyState, InboxIcon, Pill } from '@/shared/ui';

export function ResidentDetailPage() {
  const { residentId = '' } = useParams();
  const navigate = useNavigate();
  const resident = useResident(residentId);
  const reports = useReports({ residentId });

  return (
    <>
      <Breadcrumbs items={[{ label: 'Жители', to: ROUTES.residents }, { label: resident.data?.display_name ?? 'Карточка жителя' }]} />

      <AsyncState isLoading={resident.isLoading} error={resident.error} onRetry={() => void resident.refetch()}>
        {resident.data && (
          <div className="card">
            <div className="card__header">
              <div>
                <div className="card__title">{resident.data.display_name ?? 'Без имени'}</div>
                <div className="card__meta">
                  {resident.data.username ? `@${resident.data.username}` : `MAX ID ${resident.data.max_user_id ?? '—'}`}
                </div>
              </div>
            </div>
            <div className="card__body">
              <div className="stat-grid">
                <div className="stat-card">
                  <div className="stat-card__label">Дом</div>
                  <div className="stat-card__value stat-card__value--compact">
                    {resident.data.house_formatted ?? '—'}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-card__label">Город</div>
                  <div className="stat-card__value stat-card__value--compact">
                    {resident.data.house_city ?? '—'}
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-card__label">Заявок оставлено</div>
                  <div className="stat-card__value">{resident.data.reports_count}</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </AsyncState>

      <div className="card">
        <div className="card__header">
          <div className="card__title">Заявки жителя</div>
        </div>
        <div className="card__body card__body--flush">
          <AsyncState isLoading={reports.isLoading} error={reports.error} onRetry={() => void reports.refetch()}>
            {!reports.data || reports.data.length === 0 ? (
              <EmptyState icon={<InboxIcon />} title="Заявок пока нет" />
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Текст</th>
                      <th>Статус</th>
                      <th>Приоритет</th>
                      <th>Получена</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.data.map((report) => (
                      <tr
                        key={report.id}
                        className="is-clickable"
                        role="link"
                        tabIndex={0}
                        onClick={() => navigate(ROUTES.report(report.id))}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') navigate(ROUTES.report(report.id));
                        }}
                      >
                        <td className="cell-primary" data-label="Текст">{report.text ?? '—'}</td>
                        <td data-label="Статус">
                          <Pill tone={REPORT_STATUS_TONES[report.status]} label={REPORT_STATUS_LABELS[report.status]} />
                        </td>
                        <td data-label="Приоритет">
                          <Pill tone={PRIORITY_TONES[report.urgency]} label={PRIORITY_LABELS[report.urgency]} />
                        </td>
                        <td className="cell-muted" data-label="Получена">{formatDateTime(report.received_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </AsyncState>
        </div>
      </div>
    </>
  );
}
