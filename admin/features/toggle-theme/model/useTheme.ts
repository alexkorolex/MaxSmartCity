import { useCallback, useEffect, useSyncExternalStore } from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'maxsc-admin.theme';
const listeners = new Set<() => void>();

function readPreference(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  } catch {
    /* fall through to default */
  }
  return 'system';
}

let preference: ThemePreference = readPreference();

function systemScheme(): ResolvedTheme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyToDocument(resolved: ResolvedTheme): void {
  document.documentElement.setAttribute('data-theme', resolved);
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  media.addEventListener('change', listener);
  return () => {
    listeners.delete(listener);
    media.removeEventListener('change', listener);
  };
}

function getSnapshot(): ThemePreference {
  return preference;
}

export function useTheme(): {
  preference: ThemePreference;
  resolvedTheme: ResolvedTheme;
  setPreference: (next: ThemePreference) => void;
} {
  const current = useSyncExternalStore(subscribe, getSnapshot);

  const setPreference = useCallback((next: ThemePreference) => {
    preference = next;
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* preference just won't survive a reload in private mode */
    }
    for (const listener of listeners) listener();
  }, []);

  const resolvedTheme: ResolvedTheme = current === 'system' ? systemScheme() : current;

  useEffect(() => {
    applyToDocument(resolvedTheme);
  }, [resolvedTheme]);

  return { preference: current, resolvedTheme, setPreference };
}
