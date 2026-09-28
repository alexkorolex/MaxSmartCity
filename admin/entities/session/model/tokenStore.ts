import {
  clearAuthToken,
  getAuthToken,
  registerTokenRefresher,
  setAuthToken,
  subscribeUnauthorized,
} from '@/shared/api';
import { queryClient } from '@/shared/queryClient';

import { staffLogout, staffRefresh, type StaffTokens } from '../api/staffAuth';

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

registerTokenRefresher(async () => {
  try {
    const tokens = await staffRefresh();
    setAuthToken(tokens.token);
    emit();
    return true;
  } catch {
    return false;
  }
});

export function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getToken(): string | null {
  return getAuthToken();
}

export function setSession(tokens: Pick<StaffTokens, 'token'>): void {
  queryClient.clear();
  setAuthToken(tokens.token);
  emit();
}

export function clearSession(): void {
  clearAuthToken();
  queryClient.clear();
  emit();
  void staffLogout().catch(() => undefined);
}
