import { useSystemColorScheme } from '@maxhub/max-ui';
import { useCallback, useEffect, useSyncExternalStore } from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

const STORAGE_KEY = 'maxsc.theme';
const listeners = new Set<() => void>();

function readPreference(): ThemePreference {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  } catch {}
  return 'system';
}

let preference: ThemePreference = readPreference();

function applyToDocument(resolved: ResolvedTheme): void {
  document.documentElement.setAttribute('data-theme', resolved);
}

function resolveImmediately(value: ThemePreference): ResolvedTheme {
  if (value !== 'system') return value;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

applyToDocument(resolveImmediately(preference));

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
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
  const systemScheme = useSystemColorScheme({ listenChanges: true });

  const setPreference = useCallback((next: ThemePreference) => {
    preference = next;
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {}
    for (const listener of listeners) listener();
  }, []);

  const resolvedTheme: ResolvedTheme = current === 'system' ? systemScheme : current;

  useEffect(() => {
    applyToDocument(resolvedTheme);
  }, [resolvedTheme]);

  return { preference: current, resolvedTheme, setPreference };
}
