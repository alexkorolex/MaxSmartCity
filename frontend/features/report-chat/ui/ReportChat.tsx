import { Fragment, useEffect, useRef, useState, type FormEvent, type RefObject } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { notificationsQueryKey } from '@/entities/notification';
import { useChatLiveUpdates, useReportChat, useSendReportChatMessage, type ChatMessage } from '@/entities/report';
import { ArrowLeftIcon, AsyncState, SendIcon } from '@/shared/ui';

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

interface ChatHeaderProps {
  counterpart: string;
  canWrite: boolean;
  backTo: string;
  reportText?: string;
}

function ChatHeader({ counterpart, canWrite, backTo, reportText }: ChatHeaderProps) {
  return (
    <header className="report-chat__header">
      <Link className="report-chat__back" to={backTo} aria-label="Вернуться к обращению">
        <ArrowLeftIcon width={24} height={24} />
      </Link>
      <span className="report-chat__avatar" aria-hidden="true">{initials(counterpart)}</span>
      <div className="report-chat__heading">
        <span className="report-chat__eyebrow">Чат по обращению</span>
        <h1>{counterpart}</h1>
        {reportText && <p title={reportText}>{reportText}</p>}
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
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, [text]);

  return (
    <form className="chat-composer" onSubmit={onSubmit}>
      <label className="sr-only" htmlFor="resident-chat-message">Сообщение исполнителю</label>
      <div className="chat-composer__field">
        <textarea
          ref={textareaRef}
          id="resident-chat-message"
          placeholder="Напишите сообщение…"
          rows={1}
          maxLength={4000}
          value={text}
          onChange={(event) => onTextChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) {
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }
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

/**
 * Chat between the resident and organizations working on the report. Fills its parent's
 * height: only the message list scrolls, never the page around it.
 */
interface ReportChatProps {
  reportId: string;
  reportText?: string;
  backTo: string;
}

export function ReportChat({ reportId, reportText, backTo }: ReportChatProps) {
  const chat = useReportChat(reportId);
  useChatLiveUpdates(reportId, chat.isSuccess);
  const send = useSendReportChatMessage(reportId);
  const [text, setText] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const count = chat.data?.messages.length ?? 0;
  const queryClient = useQueryClient();

  useEffect(() => {
    // Every fetch of the thread also reads the "new message" notifications about it on the
    // server - refresh them so the notification badge drops right away.
    if (chat.dataUpdatedAt) void queryClient.invalidateQueries({ queryKey: notificationsQueryKey });
  }, [chat.dataUpdatedAt, queryClient]);

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
    <section className="report-chat">
      <AsyncState isLoading={chat.isLoading} error={chat.error} onRetry={() => chat.refetch()}>
        {chat.data && (
          <>
            <ChatHeader
              counterpart={chat.data.counterparts.join(', ') || 'Исполнитель обращения'}
              canWrite={chat.data.can_write}
              backTo={backTo}
              reportText={reportText}
            />
            {count > 0 ? <MessageTimeline messages={chat.data.messages} endRef={endRef} /> : <div className="report-chat__empty"><strong>Начните диалог</strong><span>Задайте вопрос по обращению — исполнитель увидит сообщение.</span></div>}
            {chat.data.can_write && <Composer text={text} pending={send.isPending} hasError={send.isError} onTextChange={setText} onSubmit={handleSubmit} />}
          </>
        )}
      </AsyncState>
    </section>
  );
}
