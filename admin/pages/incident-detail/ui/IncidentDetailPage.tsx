import { useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';

import { useCreateIncidentComment, useIncidentComments } from '@/entities/comment';
import { INCIDENT_STATUS_LABELS, INCIDENT_STATUS_TONES, useIncident } from '@/entities/incident';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { ArrowLeftIcon, AsyncState, CommentIcon, EmptyState, Pill } from '@/shared/ui';

import './IncidentDetailPage.css';

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
      <div className="page-back">
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
