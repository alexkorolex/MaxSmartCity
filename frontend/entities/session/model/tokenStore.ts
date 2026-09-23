import { clearAuthToken, getAuthToken, setAuthToken, subscribeUnauthorized } from '@/shared/api';

type Listener = () => void;

const listeners = new Set<Listener>();

function emit(): void {
  for (const listener of listeners) listener();
}

subscribeUnauthorized(() => {
  clearAuthToken();
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
  setAuthToken(token);
  emit();
}

export function clearSession(): void {
  clearAuthToken();
  emit();
}
