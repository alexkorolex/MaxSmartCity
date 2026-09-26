import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import { useCorrespondenceContacts } from '@/entities/correspondence';
import { ConversationInbox, ConversationView, NewConversationForm } from '@/features/correspondence';
import { ROUTES } from '@/shared/routes';

export function CorrespondencePage() {
  const navigate = useNavigate();
  const contacts = useCorrespondenceContacts();
  const [composing, setComposing] = useState(false);
  const canStart = (contacts.data?.length ?? 0) > 0;

  return (
    <>
      {composing && (
        <section className="card">
          <div className="card__header">
            <div>
              <div className="card__title">Новое обращение</div>
              <div className="card__meta">Администрации платформы или управляющей организации вашей территории</div>
            </div>
          </div>
          <div className="card__body">
            <NewConversationForm onStarted={(id) => navigate(ROUTES.conversation(id))} />
          </div>
        </section>
      )}
      <section className="card">
        <div className="card__header">
          <div>
            <div className="card__title">Переписка</div>
            <div className="card__meta">Органы власти, управляющие организации и администрация платформы</div>
          </div>
          {canStart && !composing && (
            <button type="button" className="btn" onClick={() => setComposing(true)}>
              Написать
            </button>
          )}
        </div>
        <div className="card__body card__body--flush">
          <ConversationInbox />
        </div>
      </section>
    </>
  );
}

export function ConversationPage() {
  const { conversationId = '' } = useParams();
  return <ConversationView key={conversationId} conversationId={conversationId} backTo={ROUTES.correspondence} />;
}
