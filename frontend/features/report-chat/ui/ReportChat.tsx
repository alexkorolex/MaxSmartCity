import { Button, Flex, Textarea, Typography } from '@maxhub/max-ui';
import { useEffect, useRef, useState } from 'react';

import { useChatLiveUpdates, useReportChat, useSendReportChatMessage, type ChatMessage } from '@/entities/report';
import { formatDateTime } from '@/shared/lib';
import { AsyncState } from '@/shared/ui';

function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={`chat-message${message.is_mine ? ' chat-message--mine' : ''}`}>
      {!message.is_mine && (
        <span className="chat-message__author">
          {message.organization_name ? `${message.organization_name} · ${message.author_name}` : message.author_name}
        </span>
      )}
      <span className="chat-message__text">{message.text}</span>
      <span className="chat-message__meta">
        {formatDateTime(message.created_at)}
        {message.is_mine && (message.read_at ? ' · прочитано' : '')}
      </span>
    </div>
  );
}

/**
 * Chat with the management company (and other organizations working on the report). While
 * it's open, new messages arrive every few seconds; when the resident is away, the bot
 * tells them in MAX.
 */
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

  const submit = () => {
    const value = text.trim();
    if (!value) return;
    send.mutate(value, { onSuccess: () => setText('') });
  };

  return (
    <Flex direction="column" gap="var(--space-3)" className="surface-card report-chat">
      <Typography.Text variant="body-strong" color="primary">
        Чат по обращению
      </Typography.Text>
      <AsyncState isLoading={chat.isLoading} error={chat.error} onRetry={() => chat.refetch()}>
        {chat.data && (
          <>
            <Typography.Text variant="description" color="secondary">
              {chat.data.can_write
                ? `Вам ответит ${chat.data.counterparts.join(', ')}. Если вы не в приложении — пришлём уведомление в MAX.`
                : 'Пока ни одна организация не взялась за обращение. Написать можно будет, когда появится исполнитель.'}
            </Typography.Text>
            {chat.data.messages.length > 0 && (
              <div className="report-chat__messages">
                {chat.data.messages.map((message) => (
                  <MessageBubble key={message.id} message={message} />
                ))}
                <div ref={endRef} />
              </div>
            )}
            {chat.data.can_write && (
              <>
                <Textarea
                  mode="primary"
                  placeholder="Ваше сообщение"
                  value={text}
                  onChange={(event) => setText(event.target.value)}
                  rows={2}
                />
                {send.isError && (
                  <Typography.Text variant="description" className="report-chat__error">
                    Не удалось отправить сообщение. Попробуйте ещё раз.
                  </Typography.Text>
                )}
                <Button variant="primary" size="medium" stretched loading={send.isPending} disabled={!text.trim()} onClick={submit}>
                  Отправить
                </Button>
              </>
            )}
          </>
        )}
      </AsyncState>
    </Flex>
  );
}
