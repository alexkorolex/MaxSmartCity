import { useLocation } from 'react-router-dom';

import { isAdmin, roleLabel, useMe, clearSession } from '@/entities/session';
import { ThemeToggle } from '@/features/toggle-theme';
import { ROUTES } from '@/shared/routes';
import { LogOutIcon } from '@/shared/ui';

const TITLES: Array<{ prefix: string; title: string; subtitle: string }> = [
  { prefix: ROUTES.organizations, title: 'Управы и жилищники', subtitle: 'Организации по городам' },
  { prefix: ROUTES.staff, title: 'Сотрудники', subtitle: 'Управы, жилищники и администраторы' },
  { prefix: ROUTES.residents, title: 'Жители', subtitle: 'Жители и их заявки' },
  { prefix: ROUTES.incidents, title: 'Инциденты', subtitle: 'Инциденты и обсуждения по ним' },
  { prefix: ROUTES.news, title: 'Новости', subtitle: 'Публикации для жителей' },
];

function resolveTitle(pathname: string): { title: string; subtitle: string } {
  const match = TITLES.find((entry) => pathname.startsWith(entry.prefix));
  if (match) return match;
  return { title: 'Обзор', subtitle: 'Общая сводка по платформе' };
}

export function Topbar() {
  const { pathname } = useLocation();
  const { title, subtitle } = resolveTitle(pathname);
  const { data: principal } = useMe();

  const primaryRole = principal ? (isAdmin(principal) ? 'admin' : (principal.roles[0] ?? '')) : '';

  return (
    <header className="admin-topbar">
      <div>
        <div className="admin-topbar__title">{title}</div>
        <div className="admin-topbar__subtitle">{subtitle}</div>
      </div>
      <div className="admin-topbar__user">
        <ThemeToggle />
        {primaryRole && <span className="admin-topbar__role">{roleLabel(primaryRole)}</span>}
        <button
          type="button"
          className="btn btn--ghost btn--small"
          onClick={() => clearSession()}
          aria-label="Выйти"
          title="Выйти"
        >
          <LogOutIcon />
        </button>
      </div>
    </header>
  );
}
