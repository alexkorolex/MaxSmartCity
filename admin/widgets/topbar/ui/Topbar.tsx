import { Link, useLocation } from 'react-router-dom';

import { clearSession, primaryRole, roleLabel, useMe } from '@/entities/session';
import { ThemeToggle } from '@/features/toggle-theme';
import { ROUTES } from '@/shared/routes';
import { LogOutIcon, MenuIcon } from '@/shared/ui';

import './Topbar.css';

const TITLES: Array<{ prefix: string; title: string; subtitle: string }> = [
  { prefix: ROUTES.organizations, title: 'Организации', subtitle: 'Управы, УК и ТСЖ' },
  { prefix: ROUTES.houses, title: 'Дома', subtitle: 'Дома в управлении УК и ТСЖ' },
  { prefix: ROUTES.messages, title: 'Сообщения', subtitle: 'Переписка с жителями по обращениям' },
  { prefix: ROUTES.staff, title: 'Сотрудники', subtitle: 'Управы, жилищники и администраторы' },
  { prefix: ROUTES.residents, title: 'Жители', subtitle: 'Жители и их заявки' },
  { prefix: ROUTES.reports, title: 'Обращение', subtitle: 'Карточка обращения' },
  { prefix: ROUTES.incidents, title: 'Инциденты', subtitle: 'Инциденты и обсуждения по ним' },
  { prefix: ROUTES.news, title: 'Новости', subtitle: 'Публикации для жителей' },
  { prefix: ROUTES.profile, title: 'Мой профиль', subtitle: 'Личные данные, пароль и уведомления' },
];

function resolveTitle(pathname: string): { title: string; subtitle: string } {
  if (/^\/reports\/[^/]+\/chat$/.test(pathname)) {
    return { title: 'Чат с жителем', subtitle: 'Переписка по обращению' };
  }
  const match = TITLES.find((entry) => pathname.startsWith(entry.prefix));
  if (match) return match;
  return { title: 'Обзор', subtitle: 'Общая сводка по платформе' };
}

interface TopbarProps {
  isMenuOpen: boolean;
  onMenuOpen: () => void;
}

export function Topbar({ isMenuOpen, onMenuOpen }: TopbarProps) {
  const { pathname } = useLocation();
  const { title, subtitle } = resolveTitle(pathname);
  const { data: principal } = useMe();

  const role = primaryRole(principal);

  return (
    <header className="admin-topbar">
      <button type="button" className="admin-topbar__menu btn btn--ghost btn--icon"
        onClick={onMenuOpen} aria-label="Открыть меню" aria-controls="admin-navigation"
        aria-expanded={isMenuOpen}>
        <MenuIcon />
      </button>
      <div className="admin-topbar__heading">
        <div className="admin-topbar__title">{title}</div>
        <div className="admin-topbar__subtitle">{subtitle}</div>
      </div>
      <div className="admin-topbar__user">
        <ThemeToggle />
        {role && (
          <Link to={ROUTES.profile} className="admin-topbar__role" title="Мой профиль">
            {roleLabel(role)}
          </Link>
        )}
        <button
          type="button"
          className="btn btn--ghost btn--small btn--icon"
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
