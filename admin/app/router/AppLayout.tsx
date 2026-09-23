import { Outlet } from 'react-router-dom';

import { Sidebar } from '@/widgets/sidebar';
import { Topbar } from '@/widgets/topbar';

export function AppLayout() {
  return (
    <div className="admin-shell">
      <Sidebar />
      <div className="admin-main">
        <Topbar />
        <main className="admin-content">
          <div className="admin-content__inner">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
