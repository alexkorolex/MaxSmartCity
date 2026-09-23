import { Counter } from '@maxhub/max-ui';
import { NavLink } from 'react-router-dom';

import { useUnreadNotificationsCount } from '@/entities/notification';
import { ROUTES } from '@/shared/routes';
import { BellIcon, HomeIcon, NewsIcon, ProfileIcon, ReportsIcon } from '@/shared/ui/icons';

import './BottomNav.css';

const ITEMS = [
  { to: ROUTES.home, label: 'Главная', Icon: HomeIcon, end: true },
  { to: ROUTES.myReports, label: 'Заявки', Icon: ReportsIcon, end: false },
  { to: ROUTES.news, label: 'Новости', Icon: NewsIcon, end: false },
  { to: ROUTES.notifications, label: 'События', Icon: BellIcon, end: false },
  { to: ROUTES.profile, label: 'Профиль', Icon: ProfileIcon, end: false },
] as const;

export function BottomNav() {
  const unreadCount = useUnreadNotificationsCount();

  return (
    <nav className="bottom-nav" aria-label="Основная навигация">
      {ITEMS.map(({ to, label, Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => `bottom-nav__item${isActive ? ' bottom-nav__item--active' : ''}`}
        >
          <span className="bottom-nav__icon">
            <Icon width={21} height={21} />
            {to === ROUTES.notifications && unreadCount > 0 && (
              <span className="bottom-nav__badge">
                <Counter value={unreadCount} variant="attention" rounded />
              </span>
            )}
          </span>
          <span className="bottom-nav__label">{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
