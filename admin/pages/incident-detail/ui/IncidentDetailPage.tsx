import { useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useCreateIncidentComment, useIncidentComments } from '@/entities/comment';
import { INCIDENT_STATUS_LABELS, INCIDENT_STATUS_TONES, useIncident } from '@/entities/incident';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { ArrowLeftIcon, AsyncState, CommentIcon, EmptyState, Pill } from '@/shared/ui';

export function IncidentDetailPage() {
  const { incidentId = '' } = useParams();
  const incident = useIncident(incidentId);
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
      <div>
        <Link to={ROUTES.incidents} className="btn btn--ghost btn--small">
          <ArrowLeftIcon width={16} height={16} />
          К списку инцидентов
        </Link>
      </div>

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

      <div className="card">
        <div className="card__header">
          <div className="card__title">Обсуждение</div>
          <div className="card__meta">Внутренние заметки и публичные комментарии по инциденту</div>
        </div>
        <div className="card__body">
          <form
            onSubmit={handleSubmit}
            style={{ display: 'flex', gap: 'var(--space-3)', marginBottom: 'var(--space-4)' }}
          >
            <input
              className="field"
              style={{ flex: 1 }}
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
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                {comments.data.map((comment) => (
                  <div key={comment.id} style={{ borderBottom: '1px solid var(--border-soft)', paddingBottom: 'var(--space-3)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 'var(--space-3)' }}>
                      <span className="cell-primary">{comment.author_display_name}</span>
                      <span className="cell-muted">{formatDateTime(comment.created_at)}</span>
                    </div>
                    <div className="cell-secondary" style={{ marginTop: 4 }}>
                      {comment.text}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </AsyncState>
        </div>
      </div>
    </>
  );
}
