import { CellAction } from '@maxhub/max-ui';
import { useNavigate } from 'react-router-dom';

import { clearSession } from '@/entities/session';
import { ROUTES } from '@/shared/routes';

export function LogoutButton() {
  const navigate = useNavigate();

  const handleLogout = () => {
    clearSession();
    navigate(ROUTES.home, { replace: true });
  };

  return (
    <CellAction mode="destructive" onClick={handleLogout}>
      Выйти
    </CellAction>
  );
}
