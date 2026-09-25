import type { CredentialsEmailResult } from '../model/types';

/** Tells the admin whether the new employee got their login by e-mail - and, if not,
 * that handing it over is now on them. */
export function CredentialsEmailNotice({ result, login }: { result: CredentialsEmailResult; login: string }) {
  if (result.sent) {
    return (
      <div className="form-success">
        Письмо со ссылкой на панель, логином «{login}» и временным паролем отправлено на {result.recipient}.
      </div>
    );
  }
  if (!result.recipient) {
    return (
      <div className="form-error">
        E-mail сотрудника не указан — передайте ему логин «{login}» и временный пароль самостоятельно.
      </div>
    );
  }
  return (
    <div className="form-error">
      Не удалось отправить письмо на {result.recipient}: {result.error}. Передайте сотруднику логин «{login}» и
      временный пароль самостоятельно.
    </div>
  );
}
