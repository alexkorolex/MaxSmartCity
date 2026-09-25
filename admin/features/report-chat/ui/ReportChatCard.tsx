import { Fragment, useEffect, useRef, useState, type FormEvent, type RefObject } from 'react';

import { useChatLiveUpdates, useChatThread, useSendChatMessage, type ChatMessage } from '@/entities/chat';
import { apiErrorMessage } from '@/shared/lib';
import { AsyncState, SendIcon } from '@/shared/ui';

import './ReportChatCard.css';

function initials(value: string): string {
  const letters = value.trim().split(/\s+/).filter(Boolean).slice(0, 2);
  return letters.map((part) => part[0]?.toUpperCase()).join('') || 'Ж';
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' }).format(new Date(value));
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

function isSameDay(first: ChatMessage, second: ChatMessage): boolean {
  return new Date(first.created_at).toDateString() === new Date(second.created_at).toDateString();
}

interface MessageProps {
  message: ChatMessage;
  compact: boolean;
  showAuthor: boolean;
  showAvatar: boolean;
}

function Message({ message, compact, showAuthor, showAvatar }: MessageProps) {
  const author = message.author_name || message.organization_name || 'Участник диалога';
  return (
    <div className={`admin-chat-row${message.is_mine ? ' admin-chat-row--mine' : ''}${compact ? ' admin-chat-row--compact' : ''}`}>
      {!message.is_mine && (
        <span className={`admin-chat-row__avatar${showAvatar ? '' : ' admin-chat-row__avatar--hidden'}`} aria-hidden="true">
          {initials(author)}
        </span>
      )}
      <div className="admin-chat-row__content">
        {showAuthor && (
          <div className="admin-chat-row__author">
            <strong>{author}</strong>
            {message.organization_name && message.organization_name !== author && <span>{message.organization_name}</span>}
          </div>
        )}
        <article className="admin-chat-bubble">
          <span className="admin-chat-bubble__text">{message.text}</span>
          <span className="admin-chat-bubble__meta">
            <time dateTime={message.created_at}>{formatTime(message.created_at)}</time>
            {message.is_mine && <span className="admin-chat-bubble__receipt" title={message.read_at ? 'Прочитано жителем' : 'Отправлено'}>{message.read_at ? '✓✓' : '✓'}</span>}
          </span>
        </article>
      </div>
    </div>
  );
}

function Timeline({ messages, endRef }: { messages: ChatMessage[]; endRef: RefObject<HTMLDivElement | null> }) {
  return (
    <div className="report-chat-card__messages" role="log" aria-label="История переписки" aria-live="polite" aria-relevant="additions">
      {messages.map((message, index) => {
        const previous = messages[index - 1];
        const next = messages[index + 1];
        const startsGroup = !previous || !isSameSender(previous, message);
        const endsGroup = !next || !isSameSender(message, next);
        return (
          <Fragment key={message.id}>
            {(!previous || !isSameDay(previous, message)) && <div className="admin-chat-day"><span>{formatDay(message.created_at)}</span></div>}
            <Message message={message} compact={!startsGroup} showAuthor={startsGroup} showAvatar={endsGroup} />
          </Fragment>
        );
      })}
      <div ref={endRef} />
    </div>
  );
}

function ChatHeader({ counterpart, subject }: { counterpart: string; subject?: string }) {
  return (
    <header className="report-chat-card__header">
      <span className="report-chat-card__avatar" aria-hidden="true">{initials(counterpart)}</span>
      <div className="report-chat-card__heading">
        <span className="report-chat-card__eyebrow">Диалог по обращению</span>
        <h2>{counterpart}</h2>
        {subject && <p className="report-chat-card__subject" title={subject}>{subject}</p>}
        <p className="report-chat-card__presence"><i aria-hidden="true" />Житель получает ответы в приложении и MAX</p>
      </div>
    </header>
  );
}

interface ComposerProps {
  text: string;
  pending: boolean;
  error: unknown;
  onTextChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

function Composer({ text, pending, error, onTextChange, onSubmit }: ComposerProps) {
  return (
    <form className="admin-chat-composer" onSubmit={onSubmit}>
      <label className="sr-only" htmlFor="report-chat-message">Сообщение жителю</label>
      <div className="admin-chat-composer__field">
        <textarea
          id="report-chat-message"
          placeholder="Напишите ответ жителю…"
          rows={1}
          maxLength={4000}
          value={text}
          onChange={(event) => onTextChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) event.currentTarget.form?.requestSubmit();
          }}
        />
        <button type="submit" aria-label="Отправить сообщение" disabled={!text.trim() || pending}>
          <SendIcon width={20} height={20} />
        </button>
      </div>
      <div className="admin-chat-composer__footer">
        <span className={error ? 'admin-chat-composer__error' : ''}>{error ? apiErrorMessage(error) : 'Ctrl/⌘ + Enter — отправить'}</span>
        <span>{text.length}/4000</span>
      </div>
    </form>
  );
}

/**
 * The organization's side of the chat with the resident who filed the report. Fills its
 * parent's height: only the message list scrolls, never the card or the page around it.
 */
export function ReportChatCard({ reportId }: { reportId: string }) {
  const chat = useChatThread(reportId);
  useChatLiveUpdates(reportId, chat.isSuccess);
  const send = useSendChatMessage(reportId);
  const [text, setText] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const count = chat.data?.messages.length ?? 0;

  useEffect(() => {
    // Scroll the message list itself to the newest message, not the page around it.
    const list = endRef.current?.parentElement;
    if (count > 0 && list) list.scrollTop = list.scrollHeight;
  }, [count]);

  const hasMessages = count > 0;
  useEffect(() => {
    // The list shrinks when the header or the composer grows, or the on-screen keyboard
    // opens - keep the newest message in view unless the user scrolled up to read.
    const list = endRef.current?.parentElement;
    if (!hasMessages || !list) return undefined;
    let pinned = true;
    const onScroll = () => {
      pinned = list.scrollHeight - list.clientHeight - list.scrollTop < 48;
    };
    const observer = new ResizeObserver(() => {
      if (pinned) list.scrollTop = list.scrollHeight;
    });
    list.addEventListener('scroll', onScroll, { passive: true });
    observer.observe(list);
    return () => {
      list.removeEventListener('scroll', onScroll);
      observer.disconnect();
    };
  }, [hasMessages]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = text.trim();
    if (value) send.mutate(value, { onSuccess: () => setText('') });
  }

  return (
    <section className="card report-chat-card">
      <AsyncState isLoading={chat.isLoading} error={chat.error} onRetry={() => void chat.refetch()}>
        {chat.data && (
          <>
            <ChatHeader counterpart={chat.data.counterparts.join(', ') || 'Житель'} subject={chat.data.report_text ?? undefined} />
            {count > 0 ? <Timeline messages={chat.data.messages} endRef={endRef} /> : <div className="report-chat-card__empty"><strong>Диалог пока пуст</strong><span>Напишите жителю первым — уведомление придёт ему в MAX.</span></div>}
            {chat.data.can_write && <Composer text={text} pending={send.isPending} error={send.isError ? send.error : null} onTextChange={setText} onSubmit={handleSubmit} />}
          </>
        )}
      </AsyncState>
    </section>
  );
}
