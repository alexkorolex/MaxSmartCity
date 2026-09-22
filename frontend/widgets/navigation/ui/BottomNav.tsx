import { Counter } from '@maxhub/max-ui';
import { NavLink } from 'react-router-dom';

import { useUnreadNotificationsCount } from '@/entities/notification';
import { ROUTES } from '@/shared/routes';

import './BottomNav.css';
import { BellIcon, HomeIcon, NewsIcon, ProfileIcon, ReportsIcon } from './icons';

const ITEMS = [
  { to: ROUTES.home, label: 'Главная', Icon: HomeIcon, end: true },
  { to: ROUTES.myReports, label: 'Обращения', Icon: ReportsIcon, end: false },
  { to: ROUTES.news, label: 'Новости', Icon: NewsIcon, end: false },
  { to: ROUTES.notifications, label: 'Уведомления', Icon: BellIcon, end: false },
  { to: ROUTES.profile, label: 'Профиль', Icon: ProfileIcon, end: false },
] as const;

export function BottomNav() {
  const unreadCount = useUnreadNotificationsCount();

  return (
    <nav className="bottom-nav">
      {ITEMS.map(({ to, label, Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => `bottom-nav__item${isActive ? ' bottom-nav__item--active' : ''}`}
        >
          <span style={{ position: 'relative' }}>
            <Icon />
            {to === ROUTES.notifications && unreadCount > 0 && (
              <span className="bottom-nav__badge">
                <Counter value={unreadCount} variant="attention" rounded />
              </span>
            )}
          </span>
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
