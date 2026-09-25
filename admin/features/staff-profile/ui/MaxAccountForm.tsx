import { useState, type FormEvent } from 'react';

import { useLinkMaxAccount, useUnlinkMaxAccount, type StaffProfile } from '@/entities/session';
import { apiErrorMessage } from '@/shared/lib';

import './StaffProfile.css';

/** Link (or unlink) the staff member's own MAX account for personal request notifications. */
export function MaxAccountForm({ profile }: { profile: StaffProfile }) {
  const link = useLinkMaxAccount();
  const unlink = useUnlinkMaxAccount();
  const [maxId, setMaxId] = useState('');

  if (profile.max_user_id !== null) {
    return (
      <div className="profile-form">
        <div className="profile-max">
          <div>
            <div className="profile-max__title">MAX привязан</div>
            <div className="cell-muted">
              ID {profile.max_user_id} — личные уведомления о заявках приходят туда
            </div>
          </div>
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => unlink.mutate()}
            disabled={unlink.isPending}
          >
            Отвязать
          </button>
        </div>
        {unlink.isError && <div className="form-error">{apiErrorMessage(unlink.error)}</div>}
      </div>
    );
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!/^\d+$/.test(maxId)) return;
    link.mutate(Number(maxId), { onSuccess: () => setMaxId('') });
  }

  return (
    <form className="profile-form" onSubmit={handleSubmit}>
      <div className="profile-link-max">
        <div>
          <label className="field-label" htmlFor="profile-max-id">
            Мой MAX ID
          </label>
          <input
            id="profile-max-id"
            className="field"
            inputMode="numeric"
            placeholder="Например, 12345678"
            value={maxId}
            onChange={(event) => setMaxId(event.target.value.replace(/\D/g, ''))}
          />
          <div className="form-hint">Напишите боту Smart City команду /id — он пришлёт ваш номер</div>
        </div>
        <button type="submit" className="btn" disabled={!maxId || link.isPending}>
          Привязать
        </button>
      </div>
      {link.isError && <div className="form-error">{apiErrorMessage(link.error)}</div>}
    </form>
  );
}
