import { useEffect, useState } from 'react';

export type MapTheme = 'light' | 'dark';

const DARK_QUERY = '(prefers-color-scheme: dark)';

function readDocumentTheme(): MapTheme | null {
  const theme = document.documentElement.dataset.theme;
  return theme === 'dark' || theme === 'light' ? theme : null;
}

function readSystemTheme(): MapTheme {
  return window.matchMedia(DARK_QUERY).matches ? 'dark' : 'light';
}

export function useResolvedTheme(): MapTheme {
  const [theme, setTheme] = useState<MapTheme>(() => readDocumentTheme() ?? readSystemTheme());

  useEffect(() => {
    const sync = () => setTheme(readDocumentTheme() ?? readSystemTheme());
    const observer = new MutationObserver(sync);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    const media = window.matchMedia(DARK_QUERY);
    media.addEventListener('change', sync);
    return () => {
      observer.disconnect();
      media.removeEventListener('change', sync);
    };
  }, []);

  return theme;
}
