import { clearAuthToken, getAuthToken, setAuthToken, subscribeUnauthorized } from '@/shared/api';
import { queryClient } from '@/shared/queryClient';

type Listener = () => void;

const listeners = new Set<Listener>();

function emit(): void {
  for (const listener of listeners) listener();
}

subscribeUnauthorized(() => {
  clearAuthToken();
  queryClient.clear();
  emit();
});

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getToken(): string | null {
  return getAuthToken();
}

export function setSession(token: string): void {
  // Clear first: a different staff member may be logging in right after another one's
  // session in the same tab, and their differently org-scoped data must never be served
  // from the previous session's cache.
  queryClient.clear();
  setAuthToken(token);
  emit();
}

export function clearSession(): void {
  clearAuthToken();
  queryClient.clear();
  emit();
}
