import { NavLink } from 'react-router-dom';

import { BuildingIcon, CityIcon, HomeIcon, NewsIcon, PersonIcon, StaffIcon, WarningIcon } from '@/shared/ui';
import { ROUTES } from '@/shared/routes';

const NAV_ITEMS = [
  { to: ROUTES.home, label: 'Обзор', icon: HomeIcon, end: true },
  { to: ROUTES.organizations, label: 'Управы и жилищники', icon: BuildingIcon, end: false },
  { to: ROUTES.staff, label: 'Сотрудники', icon: StaffIcon, end: false },
  { to: ROUTES.residents, label: 'Жители', icon: PersonIcon, end: false },
  { to: ROUTES.incidents, label: 'Инциденты', icon: WarningIcon, end: false },
  { to: ROUTES.news, label: 'Новости', icon: NewsIcon, end: false },
];

export function Sidebar() {
  return (
    <aside className="admin-sidebar">
      <div className="admin-brand">
        <span className="admin-brand__mark">
          <CityIcon width={18} height={18} />
        </span>
        <span>Smart City</span>
      </div>
      <nav className="admin-nav">
        {NAV_ITEMS.map(({ to, label, icon: ItemIcon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
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
