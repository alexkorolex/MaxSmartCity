import { useEffect, useRef } from 'react';
import { MapPinned as MapPinnedIcon } from 'lucide-react';
import { NavLink } from 'react-router-dom';

import { useChatConversations } from '@/entities/chat';
import { useConversations } from '@/entities/correspondence';
import { canBrowseOrganizations, isAdmin, isAuthority, useMe, type Principal } from '@/entities/session';
import {
  BuildingIcon,
  ChartIcon,
  CityIcon,
  CommentIcon,
  CloseIcon,
  HomeIcon,
  HousesIcon,
  MailIcon,
  MapIcon,
  NewsIcon,
  PersonIcon,
  StaffIcon,
  WarningIcon,
} from '@/shared/ui';
import { ROUTES } from '@/shared/routes';

import './Sidebar.css';

function navItems(principal: Principal | undefined) {
  const authority = isAuthority(principal);
  const ownOrganizationId = principal?.organization_id;
  const ownOrganization = ownOrganizationId
    ? [{ to: ROUTES.organization(ownOrganizationId), label: 'Моя организация', icon: authority ? CityIcon : BuildingIcon, end: false }]
    : [];
  const organizationItems = authority
    ? [...ownOrganization, { to: ROUTES.organizations, label: 'Управляющие компании', icon: BuildingIcon, end: true }]
    : canBrowseOrganizations(principal)
      ? [{ to: ROUTES.organizations, label: 'Органы власти и УК', icon: BuildingIcon, end: false }]
      : ownOrganization;
  const seesTerritories = isAdmin(principal) || authority;
  return [
    { to: ROUTES.home, label: 'Обзор', icon: HomeIcon, end: true },
    ...(seesTerritories ? [{ to: ROUTES.analytics, label: 'Статистика', icon: ChartIcon, end: false }] : []),
    ...(seesTerritories ? [{ to: ROUTES.map, label: 'Карта', icon: MapPinnedIcon, end: false }] : []),
    ...(seesTerritories
      ? [{ to: ROUTES.territories, label: authority ? 'Территория' : 'Территории', icon: MapIcon, end: false }]
      : []),
    ...organizationItems,
    { to: ROUTES.houses, label: 'Дома', icon: HousesIcon, end: false },
    ...(authority ? [] : [{ to: ROUTES.messages, label: 'Сообщения', icon: CommentIcon, end: false }]),
    { to: ROUTES.correspondence, label: 'Переписка', icon: MailIcon, end: false },
    { to: ROUTES.staff, label: 'Сотрудники', icon: StaffIcon, end: false },
    ...(authority ? [] : [{ to: ROUTES.residents, label: 'Жители', icon: PersonIcon, end: false }]),
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
  const conversations = useChatConversations(!isAuthority(principal) && Boolean(principal));
  const unread = conversations.data?.reduce((total, item) => total + item.unread_count, 0) ?? 0;
  const letters = useConversations();
  const unreadLetters = letters.data?.reduce((total, item) => total + item.unread_count, 0) ?? 0;

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
            {to === ROUTES.correspondence && unreadLetters > 0 && (
              <span className="admin-nav__badge">{unreadLetters}</span>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
