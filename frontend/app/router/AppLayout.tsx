import { Outlet, useLocation } from 'react-router-dom';

import { ROUTES } from '@/shared/routes';
import { BottomNav } from '@/widgets/navigation';

const NAV_ROUTES = new Set<string>([
  ROUTES.home,
  ROUTES.myReports,
  ROUTES.myHouse,
  ROUTES.news,
  ROUTES.notifications,
  ROUTES.profile,
]);

export function AppLayout() {
  const { pathname } = useLocation();

  return (
    <>
      <Outlet />
      {NAV_ROUTES.has(pathname) && <BottomNav />}
    </>
  );
}
