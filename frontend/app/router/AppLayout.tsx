import { Outlet } from 'react-router-dom';

import { BottomNav } from '@/widgets/navigation';

export function AppLayout() {
  return (
    <>
      <Outlet />
      <BottomNav />
    </>
  );
}
