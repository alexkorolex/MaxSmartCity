import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';

import { Sidebar } from '@/widgets/sidebar';
import { Topbar } from '@/widgets/topbar';

import './AppLayout.css';

export function AppLayout() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    if (!isMenuOpen) return undefined;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsMenuOpen(false);
    };
    document.addEventListener('keydown', closeOnEscape);
    return () => document.removeEventListener('keydown', closeOnEscape);
  }, [isMenuOpen]);

  return (
    <div className={`admin-shell${isMenuOpen ? ' admin-shell--menu-open' : ''}`}>
      <Sidebar isOpen={isMenuOpen} onClose={() => setIsMenuOpen(false)} />
      <button className="admin-shell__scrim" type="button" aria-label="Закрыть меню"
        onClick={() => setIsMenuOpen(false)} />
      <div className="admin-main" inert={isMenuOpen || undefined}>
        <Topbar isMenuOpen={isMenuOpen} onMenuOpen={() => setIsMenuOpen(true)} />
        <main className="admin-content">
          <div className="admin-content__inner">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
