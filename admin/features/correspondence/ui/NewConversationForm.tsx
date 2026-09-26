import { useState, type FormEvent } from 'react';

import { useCorrespondenceContacts, useStartConversation } from '@/entities/correspondence';
import { apiErrorMessage } from '@/shared/lib';

import './Correspondence.css';

const PLATFORM = 'platform';

export function NewConversationForm({ onStarted }: { onStarted: (conversationId: string) => void }) {
  const contacts = useCorrespondenceContacts();
  const start = useStartConversation();
  const [recipient, setRecipient] = useState('');
  const [subject, setSubject] = useState('');
  const [text, setText] = useState('');

  if (contacts.isSuccess && contacts.data.length === 0) return null;

  const canSubmit = recipient && subject.trim() && text.trim() && !start.isPending;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    start.mutate(
      {
        organization_id: recipient === PLATFORM ? null : recipient,
        subject: subject.trim(),
        text: text.trim(),
      },
      { onSuccess: (thread) => onStarted(thread.id) },
    );
  }

  return (
    <form className="new-conversation" onSubmit={handleSubmit}>
      <div className="form-grid">
        <div>
          <label className="field-label" htmlFor="conversation-recipient">
            Кому
          </label>
          <select
            id="conversation-recipient"
            className="field"
            value={recipient}
            onChange={(event) => setRecipient(event.target.value)}
          >
            <option value="">Выберите адресата</option>
            {(contacts.data ?? []).map((contact) => (
              <option key={contact.organization_id ?? PLATFORM} value={contact.organization_id ?? PLATFORM}>
                {contact.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label" htmlFor="conversation-subject">
            Тема
          </label>
          <input
            id="conversation-subject"
            className="field"
            maxLength={255}
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
          />
        </div>
        <div className="form-grid__wide">
          <label className="field-label" htmlFor="conversation-text">
            Сообщение
          </label>
          <textarea
            id="conversation-text"
            className="field"
            rows={3}
            maxLength={4000}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </div>
      </div>
      {start.isError && <div className="form-error">{apiErrorMessage(start.error)}</div>}
      <div className="form-actions">
        <button type="submit" className="btn" disabled={!canSubmit}>
          Отправить
        </button>
      </div>
    </form>
  );
}
