import { Link } from 'react-router-dom';

import { useConversations } from '@/entities/correspondence';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, CommentIcon, EmptyState } from '@/shared/ui';

import './Correspondence.css';

export function ConversationInbox() {
  const conversations = useConversations();
  return (
    <AsyncState isLoading={conversations.isLoading} error={conversations.error} onRetry={() => void conversations.refetch()}>
      {!conversations.data || conversations.data.length === 0 ? (
        <EmptyState icon={<CommentIcon />} title="Переписки пока нет" />
      ) : (
        <nav className="letter-inbox" aria-label="Переписка">
          {conversations.data.map((item) => (
            <Link
              key={item.id}
              to={ROUTES.conversation(item.id)}
              className={`letter-inbox__item${item.unread_count > 0 ? ' letter-inbox__item--unread' : ''}`}
            >
              <span className="letter-inbox__counterpart">{item.counterpart_name}</span>
              <span className="letter-inbox__subject">{item.subject}</span>
              <span className="letter-inbox__preview">{item.last_message_text}</span>
              <span className="letter-inbox__aside">
                <time dateTime={item.last_message_at}>{formatDateTime(item.last_message_at)}</time>
                {item.unread_count > 0 && (
                  <span className="letter-inbox__badge" aria-label={`Новых сообщений: ${item.unread_count}`}>
                    {item.unread_count}
                  </span>
                )}
              </span>
            </Link>
          ))}
        </nav>
      )}
    </AsyncState>
  );
}
