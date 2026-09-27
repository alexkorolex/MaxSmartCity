import { useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useCreateIncidentComment, useIncidentComments } from '@/entities/comment';
import { INCIDENT_STATUS_LABELS, INCIDENT_STATUS_TONES, useIncident, useIncidentReports } from '@/entities/incident';
import { REPORT_STATUS_LABELS, REPORT_STATUS_TONES, type ReportStatus } from '@/entities/report';
import { CompleteIncidentCard } from '@/features/complete-incident';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, Breadcrumbs, CommentIcon, EmptyState, Pill } from '@/shared/ui';

import './IncidentDetailPage.css';

export function IncidentDetailPage() {
  const { incidentId = '' } = useParams();
  const incident = useIncident(incidentId);
  const reports = useIncidentReports(incidentId);
  const comments = useIncidentComments(incidentId);
  const createComment = useCreateIncidentComment(incidentId);
  const [text, setText] = useState('');

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    createComment.mutate(
      { incident_id: incidentId, text: text.trim() },
      { onSuccess: () => setText('') },
    );
  }

  return (
    <>
      <Breadcrumbs items={[{ label: 'Инциденты', to: ROUTES.incidents }, { label: incident.data?.title ?? 'Карточка инцидента' }]} />

      <AsyncState isLoading={incident.isLoading} error={incident.error} onRetry={() => void incident.refetch()}>
        {incident.data && (
          <div className="card">
            <div className="card__header">
              <div>
                <div className="card__title">{incident.data.title}</div>
                {incident.data.description && <div className="card__meta">{incident.data.description}</div>}
              </div>
              <Pill
                tone={INCIDENT_STATUS_TONES[incident.data.status]}
                label={INCIDENT_STATUS_LABELS[incident.data.status]}
              />
            </div>
          </div>
        )}
      </AsyncState>

      {incident.data && <CompleteIncidentCard incident={incident.data} />}

      {reports.data && reports.data.length > 0 && (
        <div className="card">
          <div className="card__header">
            <div>
              <div className="card__title">Обращения жителей</div>
              <div className="card__meta">Откройте обращение, чтобы ответить жителю в чате</div>
            </div>
          </div>
          <div className="card__body card__body--flush">
            <div className="table-wrap">
              <table className="data-table">
                <tbody>
                  {reports.data.map((item) => (
                    <tr key={item.report_id}>
                      <td data-label="Обращение">
                        <Link className="cell-primary" to={ROUTES.report(item.report_id)}>
                          {item.text ?? 'Без описания'}
                        </Link>
                        <div className="cell-muted">{formatDateTime(item.received_at)}</div>
                      </td>
                      <td data-label="Статус">
                        <Pill
                          tone={REPORT_STATUS_TONES[item.status as ReportStatus] ?? 'neutral'}
                          label={REPORT_STATUS_LABELS[item.status as ReportStatus] ?? item.status}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card__header">
          <div className="card__title">Обсуждение</div>
          <div className="card__meta">Внутренние заметки и публичные комментарии по инциденту</div>
        </div>
        <div className="card__body">
          <form onSubmit={handleSubmit} className="comment-form">
            <input
              className="field"
              placeholder="Добавить комментарий…"
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
            <button type="submit" className="btn" disabled={createComment.isPending || !text.trim()}>
              Отправить
            </button>
          </form>

          <AsyncState isLoading={comments.isLoading} error={comments.error} onRetry={() => void comments.refetch()}>
            {!comments.data || comments.data.length === 0 ? (
              <EmptyState icon={<CommentIcon />} title="Комментариев пока нет" />
            ) : (
              <div className="comment-list">
                {comments.data.map((comment) => (
                  <article key={comment.id} className="comment-item">
                    <div className="comment-item__header">
                      <span className="cell-primary">{comment.author_display_name}</span>
                      <span className="cell-muted">{formatDateTime(comment.created_at)}</span>
                    </div>
                    <div className="cell-secondary comment-item__text">
                      {comment.text}
                    </div>
                  </article>
                ))}
              </div>
            )}
          </AsyncState>
        </div>
      </div>
    </>
  );
}
