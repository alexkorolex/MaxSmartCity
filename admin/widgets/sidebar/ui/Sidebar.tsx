import { useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';

import { useChatConversations } from '@/entities/chat';
import { canBrowseOrganizations, useMe, type Principal } from '@/entities/session';
import {
  BuildingIcon,
  CityIcon,
  CommentIcon,
  CloseIcon,
  HomeIcon,
  HousesIcon,
  NewsIcon,
  PersonIcon,
  StaffIcon,
  WarningIcon,
} from '@/shared/ui';
import { ROUTES } from '@/shared/routes';

import './Sidebar.css';

function navItems(principal: Principal | undefined) {
  // A housing worker never browses other organizations - only their own card.
  const organizationItem = canBrowseOrganizations(principal)
    ? { to: ROUTES.organizations, label: 'Управы и жилищники', icon: BuildingIcon, end: false }
    : principal?.organization_id
      ? { to: ROUTES.organization(principal.organization_id), label: 'Моя организация', icon: BuildingIcon, end: false }
      : null;
  return [
    { to: ROUTES.home, label: 'Обзор', icon: HomeIcon, end: true },
    ...(organizationItem ? [organizationItem] : []),
    { to: ROUTES.houses, label: 'Дома', icon: HousesIcon, end: false },
    { to: ROUTES.messages, label: 'Сообщения', icon: CommentIcon, end: false },
    { to: ROUTES.staff, label: 'Сотрудники', icon: StaffIcon, end: false },
    { to: ROUTES.residents, label: 'Жители', icon: PersonIcon, end: false },
    { to: ROUTES.incidents, label: 'Инциденты', icon: WarningIcon, end: false },
    { to: ROUTES.news, label: 'Новости', icon: NewsIcon, end: false },
    { to: ROUTES.profile, label: 'Мой профиль', icon: PersonIcon, end: false },
  ];
}

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const { data: principal } = useMe();
  const conversations = useChatConversations();
  const unread = conversations.data?.reduce((total, item) => total + item.unread_count, 0) ?? 0;

  useEffect(() => {
    if (isOpen) closeButtonRef.current?.focus();
  }, [isOpen]);

  return (
    <aside id="admin-navigation" className={`admin-sidebar${isOpen ? ' admin-sidebar--open' : ''}`}
      aria-label="Основная навигация">
      <div className="admin-brand">
        <span className="admin-brand__mark">
          <CityIcon width={18} height={18} />
        </span>
        <span className="admin-brand__copy"><strong>Smart City</strong><small>Панель управления</small></span>
        <button type="button" className="admin-sidebar__close btn btn--ghost btn--icon"
          ref={closeButtonRef} onClick={onClose} aria-label="Закрыть меню">
          <CloseIcon />
        </button>
      </div>
      <nav className="admin-nav">
        {navItems(principal).map(({ to, label, icon: ItemIcon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onClose}
            className={({ isActive }) => `admin-nav__link${isActive ? ' admin-nav__link--active' : ''}`}
          >
            <span className="admin-nav__icon">
              <ItemIcon />
            </span>
            <span>{label}</span>
            {to === ROUTES.messages && unread > 0 && <span className="admin-nav__badge">{unread}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
