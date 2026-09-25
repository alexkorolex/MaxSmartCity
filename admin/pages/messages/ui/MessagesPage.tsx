import { Link } from 'react-router-dom';

import { useChatConversations } from '@/entities/chat';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, ChevronRightIcon, CommentIcon, EmptyState } from '@/shared/ui';

import './MessagesPage.css';

function getResidentInitial(name: string | null): string {
  return name?.trim().charAt(0).toLocaleUpperCase('ru-RU') || 'Ж';
}

/** The organization's inbox: every resident chat, unread first by recency. */
export function MessagesPage() {
  const conversations = useChatConversations();

  return (
    <div className="card">
      <div className="card__header">
        <div>
          <div className="card__title">Сообщения жителей</div>
          <div className="card__meta">
            Все диалоги по обращениям. Непрочитанные сообщения всегда остаются заметными.
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
            <div className="message-inbox" aria-label="Диалоги с жителями">
              {conversations.data.map((item) => (
                <Link
                  key={item.report_id}
                  className={`message-thread${item.unread_count > 0 ? ' message-thread--unread' : ''}`}
                  to={ROUTES.report(item.report_id)}
                >
                  <span className="message-thread__avatar" aria-hidden="true">
                    {getResidentInitial(item.resident_name)}
                  </span>
                  <span className="message-thread__content">
                    <span className="message-thread__heading">
                      <strong>{item.resident_name ?? 'Житель'}</strong>
                      <time dateTime={item.last_message_at}>{formatDateTime(item.last_message_at)}</time>
                    </span>
                    <span className="message-thread__address">{item.address ?? 'Адрес не указан'}</span>
                    <strong className="message-thread__subject">{item.report_text ?? 'Обращение жителя'}</strong>
                    <span className="message-thread__preview">
                      {item.last_message_from_resident ? '' : 'Вы: '}
                      {item.last_message_text}
                    </span>
                  </span>
                  <span className="message-thread__aside">
                    {item.unread_count > 0 ? (
                      <span
                        className="message-thread__badge"
                        aria-label={`Новых сообщений: ${item.unread_count}`}
                      >
                        {item.unread_count}
                      </span>
                    ) : null}
                    <ChevronRightIcon width={18} height={18} />
                  </span>
                </Link>
              ))}
            </div>
          )}
        </AsyncState>
      </div>
    </div>
  );
}
