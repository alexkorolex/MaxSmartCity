import { useEffect, useRef, useState, type FormEvent } from 'react';

import { useChatLiveUpdates, useChatThread, useSendChatMessage, type ChatMessage } from '@/entities/chat';
import { apiErrorMessage, formatDateTime } from '@/shared/lib';
import { AsyncState } from '@/shared/ui';

import './ReportChatCard.css';

function Bubble({ message }: { message: ChatMessage }) {
  const author = message.organization_name
    ? `${message.author_name} · ${message.organization_name}`
    : message.author_name;
  return (
    <article className={`chat-bubble${message.is_mine ? ' chat-bubble--mine' : ''}`}>
      <div className="chat-bubble__author">{author}</div>
      <div className="chat-bubble__text">{message.text}</div>
      <div className="chat-bubble__meta">
        {formatDateTime(message.created_at)}
        {message.is_mine && message.read_at ? ' · прочитано жителем' : ''}
      </div>
    </article>
  );
}

/** The organization's side of the chat with the resident who filed the report. */
export function ReportChatCard({ reportId }: { reportId: string }) {
  const chat = useChatThread(reportId);
  useChatLiveUpdates(reportId, chat.isSuccess);
  const send = useSendChatMessage(reportId);
  const [text, setText] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const count = chat.data?.messages.length ?? 0;

  useEffect(() => {
    if (count > 0) endRef.current?.scrollIntoView({ block: 'nearest' });
  }, [count]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const value = text.trim();
    if (value) send.mutate(value, { onSuccess: () => setText('') });
  }

  return (
    <div className="card">
      <div className="card__header">
        <div>
          <div className="card__title">Чат с жителем</div>
          <div className="card__meta">
            {chat.data ? `Собеседник: ${chat.data.counterparts.join(', ')}. ` : ''}
            Если житель не в приложении, ответ придёт ему в MAX.
          </div>
        </div>
      </div>
      <div className="card__body report-chat-card">
        <AsyncState isLoading={chat.isLoading} error={chat.error} onRetry={() => void chat.refetch()}>
          {count === 0 ? (
            <div className="cell-muted">Сообщений пока нет — напишите жителю первым.</div>
          ) : (
            <div
              className="report-chat-card__messages"
              role="log"
              aria-label="История переписки"
              aria-live="polite"
              aria-relevant="additions"
            >
              {chat.data?.messages.map((message) => (
                <Bubble key={message.id} message={message} />
              ))}
              <div ref={endRef} />
            </div>
          )}
        </AsyncState>
        <form className="report-chat-card__form" onSubmit={handleSubmit}>
          <label className="sr-only" htmlFor="report-chat-message">Сообщение жителю</label>
          <textarea
            id="report-chat-message"
            className="field"
            placeholder="Напишите ответ жителю…"
            rows={3}
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) handleSubmit(event);
            }}
          />
          {send.isError && <div className="form-error">{apiErrorMessage(send.error)}</div>}
          <div className="form-actions report-chat-card__actions">
            <button type="submit" className="btn" disabled={!text.trim() || send.isPending}>
              {send.isPending ? 'Отправляем…' : 'Отправить'}
            </button>
            <span className="form-hint">Ctrl/⌘ + Enter</span>
          </div>
        </form>
      </div>
    </div>
  );
}
