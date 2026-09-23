import { Outlet } from 'react-router-dom';

import { useSession } from '@/entities/session';
import { StaffLoginForm } from '@/features/staff-login';

export function RequireStaffSession() {
  const { isAuthenticated } = useSession();

  if (!isAuthenticated) return <StaffLoginForm />;

  return <Outlet />;
}
