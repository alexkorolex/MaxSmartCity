import { useState, type FormEvent } from 'react';

import { useStaffLogin } from '@/entities/session';
import { isApiError } from '@/shared/api';
import { CityIcon } from '@/shared/ui';

import './StaffLoginForm.css';

function errorMessage(error: unknown): string {
  if (isApiError(error)) {
    if (error.status === 401) return 'Неверный логин или пароль';
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'Что-то пошло не так';
}

export function StaffLoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const login = useStaffLogin();

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!username || !password) return;
    login.mutate({ username, password });
  }

  return (
    <div className="auth-screen">
      <div className="card auth-card">
        <span className="auth-card__mark">
          <CityIcon width={28} height={28} />
        </span>
        <div className="auth-card__eyebrow">Панель управления</div>
        <h1>Smart City</h1>
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
      </div>
    </div>
  );
}
