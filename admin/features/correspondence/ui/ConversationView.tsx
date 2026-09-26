import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';

import {
  useConversation,
  useConversationLiveUpdates,
  useSendConversationMessage,
  type ConversationMessage,
} from '@/entities/correspondence';
import { apiErrorMessage, formatDateTime } from '@/shared/lib';
import { ArrowLeftIcon, AsyncState, SendIcon } from '@/shared/ui';

import './Correspondence.css';

function Message({ message, read }: { message: ConversationMessage; read: boolean }) {
  return (
    <div className={`letter${message.is_mine ? ' letter--mine' : ''}`}>
      <div className="letter__author">
        <strong>{message.author_name}</strong>
        <span>{message.organization_name}</span>
      </div>
      <div className="letter__bubble">
        <span className="letter__text">{message.text}</span>
        <span className="letter__meta">
          <time dateTime={message.created_at}>{formatDateTime(message.created_at)}</time>
          {message.is_mine && <span title={read ? 'Прочитано' : 'Отправлено'}>{read ? '✓✓' : '✓'}</span>}
        </span>
      </div>
    </div>
  );
}

export function ConversationView({ conversationId, backTo }: { conversationId: string; backTo: string }) {
  const conversation = useConversation(conversationId);
  useConversationLiveUpdates(conversationId, conversation.isSuccess);
  const send = useSendConversationMessage(conversationId);
  const [text, setText] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const count = conversation.data?.messages.length ?? 0;
  const readAt = conversation.data?.counterpart_read_at ? Date.parse(conversation.data.counterpart_read_at) : null;

  useEffect(() => {
    const list = endRef.current?.parentElement;
    if (count > 0 && list) list.scrollTop = list.scrollHeight;
  }, [count]);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const value = text.trim();
    if (value) send.mutate(value, { onSuccess: () => setText('') });
  }

  return (
    <section className="card conversation">
      <AsyncState
        isLoading={conversation.isLoading}
        error={conversation.error}
        onRetry={() => void conversation.refetch()}
      >
        {conversation.data && (
          <>
            <header className="conversation__header">
              <Link className="btn btn--ghost btn--icon" to={backTo} aria-label="К списку переписки">
                <ArrowLeftIcon />
              </Link>
              <div>
                <div className="conversation__counterpart">{conversation.data.counterpart_name}</div>
                <h2 className="conversation__subject">{conversation.data.subject}</h2>
              </div>
            </header>
            <div className="conversation__messages" role="log" aria-live="polite" aria-label="Переписка">
              {conversation.data.messages.map((message) => (
                <Message
                  key={message.id}
                  message={message}
                  read={readAt !== null && Date.parse(message.created_at) <= readAt}
                />
              ))}
              <div ref={endRef} />
            </div>
            <form className="conversation__composer" onSubmit={handleSubmit}>
              <label className="sr-only" htmlFor="conversation-message">
                Сообщение
              </label>
              <textarea
                id="conversation-message"
                className="field"
                rows={2}
                maxLength={4000}
                placeholder="Напишите ответ…"
                value={text}
                onChange={(event) => setText(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
              />
              <button type="submit" className="btn" disabled={!text.trim() || send.isPending} aria-label="Отправить">
                <SendIcon />
              </button>
              {send.isError && <div className="form-error">{apiErrorMessage(send.error)}</div>}
            </form>
          </>
        )}
      </AsyncState>
    </section>
  );
}
