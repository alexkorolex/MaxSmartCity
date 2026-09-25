import { Fragment, useEffect, useRef, useState, type FormEvent, type RefObject } from 'react';

import { useChatLiveUpdates, useReportChat, useSendReportChatMessage, type ChatMessage } from '@/entities/report';
import { AsyncState, SendIcon } from '@/shared/ui';

import './ReportChat.css';

function initials(value: string): string {
  const letters = value.trim().split(/\s+/).filter(Boolean).slice(0, 2);
  return letters.map((part) => part[0]?.toUpperCase()).join('') || 'УК';
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

function isSameDay(first: string, second: string): boolean {
  return new Date(first).toDateString() === new Date(second).toDateString();
}

function formatDay(value: string): string {
  const date = new Date(value);
  if (date.toDateString() === new Date().toDateString()) return 'Сегодня';
  return new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' }).format(date);
}

function isSameSender(first: ChatMessage, second: ChatMessage): boolean {
  return first.is_mine === second.is_mine
    && first.author_name === second.author_name
    && first.organization_name === second.organization_name;
}

interface MessageProps {
  message: ChatMessage;
  compact: boolean;
  showAuthor: boolean;
  showAvatar: boolean;
}

function Message({ message, compact, showAuthor, showAvatar }: MessageProps) {
  const sender = message.organization_name ?? message.author_name;
  return (
    <div className={`chat-row${message.is_mine ? ' chat-row--mine' : ''}${compact ? ' chat-row--compact' : ''}`}>
      {!message.is_mine && (
        <span className={`chat-row__avatar${showAvatar ? '' : ' chat-row__avatar--hidden'}`} aria-hidden="true">
          {initials(sender)}
        </span>
      )}
      <div className="chat-row__content">
        {showAuthor && !message.is_mine && (
          <div className="chat-row__author">
            <strong>{sender}</strong>
            {message.organization_name && <span>{message.author_name}</span>}
          </div>
        )}
        <article className="chat-message">
          <span className="chat-message__text">{message.text}</span>
          <span className="chat-message__meta">
            <time dateTime={message.created_at}>{formatTime(message.created_at)}</time>
            {message.is_mine && <span className="chat-message__receipt" title={message.read_at ? 'Прочитано' : 'Отправлено'}>{message.read_at ? '✓✓' : '✓'}</span>}
          </span>
        </article>
      </div>
    </div>
  );
}

function MessageTimeline({ messages, endRef }: { messages: ChatMessage[]; endRef: RefObject<HTMLDivElement | null> }) {
  return (
    <div className="report-chat__messages" role="log" aria-label="История переписки" aria-live="polite" aria-relevant="additions">
      {messages.map((message, index) => {
        const previous = messages[index - 1];
        const next = messages[index + 1];
        const startsGroup = !previous || !isSameSender(previous, message);
        const endsGroup = !next || !isSameSender(message, next);
        return (
          <Fragment key={message.id}>
            {(!previous || !isSameDay(previous.created_at, message.created_at)) && <div className="chat-day"><span>{formatDay(message.created_at)}</span></div>}
            <Message message={message} compact={!startsGroup} showAuthor={startsGroup} showAvatar={endsGroup} />
          </Fragment>
        );
      })}
      <div ref={endRef} />
    </div>
  );
}

function ChatHeader({ counterpart, canWrite }: { counterpart: string; canWrite: boolean }) {
  return (
    <header className="report-chat__header">
      <span className="report-chat__avatar" aria-hidden="true">{initials(counterpart)}</span>
      <div className="report-chat__heading">
        <h2>Чат по обращению</h2>
        <p>{counterpart}</p>
        <span className={`report-chat__presence${canWrite ? '' : ' report-chat__presence--muted'}`}>
          <i aria-hidden="true" />
          {canWrite ? 'Ответы придут сюда и в MAX' : 'Ожидаем назначения исполнителя'}
        </span>
      </div>
    </header>
  );
}

interface ComposerProps {
  text: string;
  pending: boolean;
  hasError: boolean;
  onTextChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

function Composer({ text, pending, hasError, onTextChange, onSubmit }: ComposerProps) {
  return (
    <form className="chat-composer" onSubmit={onSubmit}>
      <label className="sr-only" htmlFor="resident-chat-message">Сообщение исполнителю</label>
      <div className="chat-composer__field">
        <textarea
          id="resident-chat-message"
          placeholder="Напишите сообщение…"
          rows={1}
          maxLength={4000}
          value={text}
          onChange={(event) => onTextChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) event.currentTarget.form?.requestSubmit();
          }}
        />
        <button type="submit" aria-label="Отправить сообщение" disabled={!text.trim() || pending}>
          <SendIcon width={21} height={21} />
        </button>
      </div>
      <div className="chat-composer__footer">
        <span className={hasError ? 'chat-composer__error' : ''}>{hasError ? 'Не удалось отправить. Попробуйте ещё раз.' : 'Ctrl/⌘ + Enter — отправить'}</span>
        <span>{text.length}/4000</span>
      </div>
    </form>
  );
}

/** Chat between the resident and organizations working on the report. */
export function ReportChat({ reportId }: { reportId: string }) {
  const chat = useReportChat(reportId);
  useChatLiveUpdates(reportId, chat.isSuccess);
  const send = useSendReportChatMessage(reportId);
  const [text, setText] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const count = chat.data?.messages.length ?? 0;

  useEffect(() => {
    if (count > 0) endRef.current?.scrollIntoView({ block: 'nearest' });
  }, [count]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = text.trim();
    if (value) send.mutate(value, { onSuccess: () => setText('') });
  }

  return (
    <section className="surface-card report-chat">
      <AsyncState isLoading={chat.isLoading} error={chat.error} onRetry={() => chat.refetch()}>
        {chat.data && (
          <>
            <ChatHeader counterpart={chat.data.counterparts.join(', ') || 'Исполнитель обращения'} canWrite={chat.data.can_write} />
            {count > 0 ? <MessageTimeline messages={chat.data.messages} endRef={endRef} /> : <div className="report-chat__empty"><strong>Начните диалог</strong><span>Задайте вопрос по обращению — исполнитель увидит сообщение.</span></div>}
            {chat.data.can_write && <Composer text={text} pending={send.isPending} hasError={send.isError} onTextChange={setText} onSubmit={handleSubmit} />}
          </>
        )}
      </AsyncState>
    </section>
  );
}
