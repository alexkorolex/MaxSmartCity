import { useEffect, useRef } from 'react';
import { NavLink } from 'react-router-dom';

import { BuildingIcon, CityIcon, CloseIcon, HomeIcon, NewsIcon, PersonIcon, StaffIcon, WarningIcon } from '@/shared/ui';
import { ROUTES } from '@/shared/routes';

import './Sidebar.css';

const NAV_ITEMS = [
  { to: ROUTES.home, label: 'Обзор', icon: HomeIcon, end: true },
  { to: ROUTES.organizations, label: 'Управы и жилищники', icon: BuildingIcon, end: false },
  { to: ROUTES.staff, label: 'Сотрудники', icon: StaffIcon, end: false },
  { to: ROUTES.residents, label: 'Жители', icon: PersonIcon, end: false },
  { to: ROUTES.incidents, label: 'Инциденты', icon: WarningIcon, end: false },
  { to: ROUTES.news, label: 'Новости', icon: NewsIcon, end: false },
];

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

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
        {NAV_ITEMS.map(({ to, label, icon: ItemIcon, end }) => (
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
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
