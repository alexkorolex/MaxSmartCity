import { MoonIcon, SunIcon } from '@/shared/ui';

import { useTheme } from '../model/useTheme';

export function ThemeToggle() {
  const { resolvedTheme, setPreference } = useTheme();
  const next = resolvedTheme === 'dark' ? 'light' : 'dark';

  return (
    <button
      type="button"
      className="btn btn--ghost btn--small"
      onClick={() => setPreference(next)}
      aria-label={resolvedTheme === 'dark' ? 'Включить светлую тему' : 'Включить тёмную тему'}
      title={resolvedTheme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
    >
      {resolvedTheme === 'dark' ? <SunIcon /> : <MoonIcon />}
    </button>
  );
}
