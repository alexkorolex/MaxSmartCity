import { MIN_PASSWORD_LENGTH } from '../lib/staffAccount';
import type { StaffAccountPayload } from '../model/types';

interface StaffAccountFieldsProps {
  idPrefix: string;
  value: StaffAccountPayload;
  onChange: (value: StaffAccountPayload) => void;
}

/** Login, password, name and e-mail of a new employee account (Keycloak, role «Жилищник»). */
export function StaffAccountFields({ idPrefix, value, onChange }: StaffAccountFieldsProps) {
  const passwordTooShort = value.password.length > 0 && value.password.length < MIN_PASSWORD_LENGTH;

  return (
    <div className="form-grid">
      <div>
        <label className="field-label" htmlFor={`${idPrefix}-name`}>
          ФИО сотрудника
        </label>
        <input
          id={`${idPrefix}-name`}
          className="field"
          placeholder="Иванов Иван"
          value={value.display_name}
          onChange={(event) => onChange({ ...value, display_name: event.target.value })}
        />
      </div>
      <div>
        <label className="field-label" htmlFor={`${idPrefix}-email`}>
          E-mail
        </label>
        <input
          id={`${idPrefix}-email`}
          className="field"
          type="email"
          placeholder="dispatcher@uk.ru"
          value={value.email ?? ''}
          onChange={(event) => onChange({ ...value, email: event.target.value })}
        />
        <div className="form-hint">Сюда придёт письмо со ссылкой на панель, логином и паролем</div>
      </div>
      <div>
        <label className="field-label" htmlFor={`${idPrefix}-login`}>
          Логин
        </label>
        <input
          id={`${idPrefix}-login`}
          className="field"
          autoComplete="off"
          placeholder="uk-dispatcher"
          value={value.login}
          onChange={(event) => onChange({ ...value, login: event.target.value })}
        />
      </div>
      <div>
        <label className="field-label" htmlFor={`${idPrefix}-password`}>
          Временный пароль
        </label>
        <input
          id={`${idPrefix}-password`}
          className="field"
          type="password"
          autoComplete="new-password"
          value={value.password}
          onChange={(event) => onChange({ ...value, password: event.target.value })}
        />
        <div className={passwordTooShort ? 'form-hint form-hint--error' : 'form-hint'}>
          Не короче {MIN_PASSWORD_LENGTH} символов. Сотрудник получит его в письме.
        </div>
      </div>
    </div>
  );
}
