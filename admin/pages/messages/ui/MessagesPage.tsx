import { useNavigate } from 'react-router-dom';

import { useChatConversations } from '@/entities/chat';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, CommentIcon, EmptyState, Pill } from '@/shared/ui';

/** The organization's inbox: every resident chat, unread first by recency. */
export function MessagesPage() {
  const navigate = useNavigate();
  const conversations = useChatConversations();

  return (
    <div className="card">
      <div className="card__header">
        <div>
          <div className="card__title">Сообщения жителей</div>
          <div className="card__meta">
            Переписка по обращениям жителей ваших домов. Непрочитанные сообщения дублируются в выбранные
            организацией каналы уведомлений.
          </div>
        </div>
      </div>
      <div className="card__body card__body--flush">
        <AsyncState
          isLoading={conversations.isLoading}
          error={conversations.error}
          onRetry={() => void conversations.refetch()}
        >
          {!conversations.data || conversations.data.length === 0 ? (
            <EmptyState icon={<CommentIcon />} title="Сообщений пока нет" />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Житель</th>
                    <th>Обращение</th>
                    <th>Последнее сообщение</th>
                    <th>Когда</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {conversations.data.map((item) => (
                    <tr
                      key={item.report_id}
                      className="is-clickable"
                      tabIndex={0}
                      onClick={() => navigate(ROUTES.report(item.report_id))}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') navigate(ROUTES.report(item.report_id));
                      }}
                    >
                      <td data-label="Житель">
                        <div className="cell-primary">{item.resident_name ?? 'Житель'}</div>
                        <div className="cell-muted">{item.address ?? '—'}</div>
                      </td>
                      <td className="cell-secondary" data-label="Обращение">
                        {(item.report_text ?? '—').slice(0, 80)}
                      </td>
                      <td className="cell-secondary" data-label="Последнее сообщение">
                        {item.last_message_from_resident ? '' : 'Вы: '}
                        {item.last_message_text.slice(0, 120)}
                      </td>
                      <td className="cell-muted" data-label="Когда">{formatDateTime(item.last_message_at)}</td>
                      <td data-label="Статус">
                        {item.unread_count > 0 && <Pill tone="info" label={`Новых: ${item.unread_count}`} />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </AsyncState>
      </div>
    </div>
  );
}
