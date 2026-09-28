import { useState, type FormEvent } from 'react';

import { useStaffInitialPassword, useStaffLogin } from '@/entities/session';
import { isApiError } from '@/shared/api';
import { CityIcon } from '@/shared/ui';

import './StaffLoginForm.css';

const MIN_PASSWORD_LENGTH = 8;

function errorMessage(error: unknown): string {
  if (isApiError(error)) {
    if (error.status === 401) return 'Неверный логин или пароль';
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'Что-то пошло не так';
}

function requiresPasswordChange(error: unknown): boolean {
  if (!isApiError(error) || error.status !== 403) return false;
  const extra = (error.detail as { extra?: { code?: unknown } } | undefined)?.extra;
  return extra?.code === 'password_change_required';
}

export function StaffLoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [repeatPassword, setRepeatPassword] = useState('');
  const [mismatch, setMismatch] = useState<string | null>(null);
  const login = useStaffLogin();
  const initialPassword = useStaffInitialPassword();
  const changingPassword = requiresPasswordChange(login.error);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!username || !password) return;
    login.mutate({ username, password });
  }

  function handleChange(event: FormEvent) {
    event.preventDefault();
    if (newPassword.length < MIN_PASSWORD_LENGTH) {
      setMismatch(`Пароль должен быть не короче ${MIN_PASSWORD_LENGTH} символов`);
      return;
    }
    if (newPassword !== repeatPassword) {
      setMismatch('Пароли не совпадают');
      return;
    }
    setMismatch(null);
    initialPassword.mutate({ username, password, newPassword });
  }

  return (
    <div className="auth-screen">
      <div className="card auth-card">
        <span className="auth-card__mark">
          <CityIcon width={28} height={28} />
        </span>
        <div className="auth-card__eyebrow">Панель управления</div>
        <h1>Smart City</h1>
        {changingPassword ? (
          <>
            <p>Вы вошли с временным паролем. Придумайте собственный, чтобы продолжить.</p>
            <form className="auth-form" onSubmit={handleChange}>
              <div>
                <label className="field-label" htmlFor="new-password">
                  Новый пароль
                </label>
                <input
                  id="new-password"
                  className="field"
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  autoFocus
                  placeholder={`Не короче ${MIN_PASSWORD_LENGTH} символов`}
                />
              </div>
              <div>
                <label className="field-label" htmlFor="repeat-password">
                  Повторите пароль
                </label>
                <input
                  id="repeat-password"
                  className="field"
                  type="password"
                  autoComplete="new-password"
                  value={repeatPassword}
                  onChange={(event) => setRepeatPassword(event.target.value)}
                />
              </div>
              {(mismatch || initialPassword.isError) && (
                <div className="auth-error">{mismatch ?? errorMessage(initialPassword.error)}</div>
              )}
              <button type="submit" className="btn" disabled={initialPassword.isPending}>
                {initialPassword.isPending ? 'Сохраняем…' : 'Сохранить и войти'}
              </button>
              <button type="button" className="btn btn--ghost" onClick={() => login.reset()}>
                Назад
              </button>
            </form>
          </>
        ) : (
          <>
            <p>Единое рабочее пространство для городских служб и администраторов</p>
            <form className="auth-form" onSubmit={handleSubmit}>
              <div>
                <label className="field-label" htmlFor="username">
                  Логин
                </label>
                <input
                  id="username"
                  className="field"
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  autoFocus
                  placeholder="Введите логин"
                />
              </div>
              <div>
                <label className="field-label" htmlFor="password">
                  Пароль
                </label>
                <input
                  id="password"
                  className="field"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Введите пароль"
                />
              </div>
              {login.isError && <div className="auth-error">{errorMessage(login.error)}</div>}
              <button type="submit" className="btn" disabled={login.isPending}>
                {login.isPending ? 'Входим…' : 'Войти'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
