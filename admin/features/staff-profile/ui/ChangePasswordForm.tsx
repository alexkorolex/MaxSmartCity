import { useState, type FormEvent } from 'react';

import { MIN_PASSWORD_LENGTH } from '@/entities/organization';
import { useChangePassword } from '@/entities/session';
import { isApiError } from '@/shared/api';
import { apiErrorMessage } from '@/shared/lib';

import './StaffProfile.css';

function passwordErrorMessage(error: unknown): string {
  if (isApiError(error) && error.message.startsWith('Current password is incorrect')) {
    return 'Текущий пароль указан неверно';
  }
  if (isApiError(error) && error.message.startsWith('Invalid password')) {
    return `Пароль не подходит под требования безопасности: ${error.message}`;
  }
  return apiErrorMessage(error);
}

/** Change one's own password - the current one is re-checked on the server. */
export function ChangePasswordForm() {
  const change = useChangePassword();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [repeat, setRepeat] = useState('');

  const tooShort = next.length > 0 && next.length < MIN_PASSWORD_LENGTH;
  const mismatch = repeat.length > 0 && repeat !== next;
  const canSubmit = current && next.length >= MIN_PASSWORD_LENGTH && repeat === next && !change.isPending;

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canSubmit) return;
    change.mutate(
      { current_password: current, new_password: next },
      {
        onSuccess: () => {
          setCurrent('');
          setNext('');
          setRepeat('');
        },
      },
    );
  }

  return (
    <form className="profile-form" onSubmit={handleSubmit}>
      <div className="form-grid">
        <div className="form-grid__wide">
          <label className="field-label" htmlFor="password-current">
            Текущий пароль
          </label>
          <input
            id="password-current"
            className="field"
            type="password"
            autoComplete="current-password"
            value={current}
            onChange={(event) => setCurrent(event.target.value)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="password-new">
            Новый пароль
          </label>
          <input
            id="password-new"
            className="field"
            type="password"
            autoComplete="new-password"
            value={next}
            onChange={(event) => setNext(event.target.value)}
            aria-invalid={tooShort || undefined}
          />
          <div className={`form-hint${tooShort ? ' form-hint--error' : ''}`}>
            Не короче {MIN_PASSWORD_LENGTH} символов
          </div>
        </div>
        <div>
          <label className="field-label" htmlFor="password-repeat">
            Повторите новый пароль
          </label>
          <input
            id="password-repeat"
            className="field"
            type="password"
            autoComplete="new-password"
            value={repeat}
            onChange={(event) => setRepeat(event.target.value)}
            aria-invalid={mismatch || undefined}
          />
          {mismatch && <div className="form-hint form-hint--error">Пароли не совпадают</div>}
        </div>
      </div>
      {change.isError && <div className="form-error">{passwordErrorMessage(change.error)}</div>}
      {change.isSuccess && <div className="form-success">Пароль изменён. Используйте его при следующем входе.</div>}
      <div className="form-actions">
        <button type="submit" className="btn" disabled={!canSubmit}>
          {change.isPending ? 'Меняем…' : 'Сменить пароль'}
        </button>
      </div>
    </form>
  );
}
