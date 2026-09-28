import { useState, type FormEvent } from 'react';

import { useUpdateProfile, type StaffProfile } from '@/entities/session';
import { isApiError } from '@/shared/api';
import { apiErrorMessage } from '@/shared/lib';

import './StaffProfile.css';

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function updateErrorMessage(error: unknown): string {
  if (isApiError(error) && error.status === 409) return 'Этот e-mail уже используется другой учётной записью';
  return apiErrorMessage(error);
}

export function ProfileDetailsForm({ profile }: { profile: StaffProfile }) {
  const update = useUpdateProfile();
  const [displayName, setDisplayName] = useState(profile.display_name);
  const [email, setEmail] = useState(profile.email ?? '');

  const trimmedEmail = email.trim();
  const emailInvalid = trimmedEmail !== '' && !EMAIL_PATTERN.test(trimmedEmail);
  const isDirty = displayName.trim() !== profile.display_name || trimmedEmail !== (profile.email ?? '');

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!displayName.trim() || emailInvalid) return;
    update.mutate({ display_name: displayName.trim(), email: trimmedEmail || null });
  }

  return (
    <form className="profile-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <div>
          <label className="field-label" htmlFor="profile-name">
            ФИО
          </label>
          <input
            id="profile-name"
            className="field"
            autoComplete="name"
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            required
          />
        </div>
        <div>
          <label className="field-label" htmlFor="profile-email">
            E-mail
          </label>
          <input
            id="profile-email"
            className="field"
            type="email"
            autoComplete="email"
            placeholder="name@uk.ru"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={emailInvalid || undefined}
          />
          <div className={`form-hint${emailInvalid ? ' form-hint--error' : ''}`}>
            {emailInvalid ? 'Проверьте адрес почты' : 'На неё приходят письма от панели управления'}
          </div>
        </div>
        <div>
          <label className="field-label" htmlFor="profile-login">
            Логин
          </label>
          <input id="profile-login" className="field" value={profile.login} readOnly disabled />
          <div className="form-hint">Логин меняет администратор платформы</div>
        </div>
      </div>
      {update.isError && <div className="form-error">{updateErrorMessage(update.error)}</div>}
      {update.isSuccess && !isDirty && <div className="form-success">Данные сохранены</div>}
      <div className="form-actions">
        <button
          type="submit"
          className="btn"
          disabled={!isDirty || !displayName.trim() || emailInvalid || update.isPending}
        >
          {update.isPending ? 'Сохраняем…' : 'Сохранить'}
        </button>
      </div>
    </form>
  );
}
