import { useState, type FormEvent } from 'react';

import { COMPLETABLE_INCIDENT_STATUSES, useCompleteIncident, type Incident } from '@/entities/incident';
import { isApiError } from '@/shared/api';
import { apiErrorMessage } from '@/shared/lib';

import './CompleteIncidentCard.css';

const OPEN_ELSEWHERE = 'Other required assignments are still open: ';

function completionError(error: unknown): string {
  if (isApiError(error) && error.message.startsWith(OPEN_ELSEWHERE)) {
    return `Работы ещё не завершили другие обязательные исполнители: ${error.message.slice(OPEN_ELSEWHERE.length)}`;
  }
  return apiErrorMessage(error);
}

/**
 * "Работы выполнены": the staff member's organization finished its part. The incident
 * moves to «Решён», residents get asked to confirm, and it closes on their confirmation
 * or automatically after 3 days.
 */
export function CompleteIncidentCard({ incident }: { incident: Incident }) {
  const [comment, setComment] = useState('');
  const complete = useCompleteIncident(incident.id);

  if (!COMPLETABLE_INCIDENT_STATUSES.has(incident.status)) return null;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    complete.mutate(comment.trim() || null, { onSuccess: () => setComment('') });
  }

  return (
    <div className="card">
      <div className="card__header">
        <div>
          <div className="card__title">Работы выполнены?</div>
          <div className="card__meta">
            Заявка перейдёт в статус «Решён», жители получат уведомление и подтвердят результат. Если не ответят
            в течение 3 дней, заявка закроется автоматически.
          </div>
        </div>
      </div>
      <div className="card__body">
        <form className="complete-incident" onSubmit={handleSubmit}>
          <textarea
            className="field"
            placeholder="Что сделано (увидят жители в уведомлении). Необязательно"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
          />
          {complete.isError && <div className="form-error">{completionError(complete.error)}</div>}
          <div className="form-actions">
            <button type="submit" className="btn" disabled={complete.isPending}>
              {complete.isPending ? 'Сохраняем…' : 'Работы выполнены — закрыть заявку'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
