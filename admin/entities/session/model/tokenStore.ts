import {
  clearAuthToken,
  getAuthToken,
  getRefreshToken,
  registerTokenRefresher,
  setAuthToken,
  setRefreshToken,
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

// The access token lives 5 minutes; the transport calls this on a 401 to renew it with the
// refresh token, so a staff member stays signed in for the whole 24-hour session.
registerTokenRefresher(async () => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  try {
    const tokens = await staffRefresh(refreshToken);
    setAuthToken(tokens.token);
    setRefreshToken(tokens.refresh_token ?? refreshToken);
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

export function setSession(tokens: Pick<StaffTokens, 'token' | 'refresh_token'>): void {
  // Clear first: a different staff member may be logging in right after another one's
  // session in the same tab, and their differently org-scoped data must never be served
  // from the previous session's cache.
  queryClient.clear();
  setAuthToken(tokens.token);
  setRefreshToken(tokens.refresh_token);
  emit();
}

export function clearSession(): void {
  const refreshToken = getRefreshToken();
  clearAuthToken();
  queryClient.clear();
  emit();
  // End the Keycloak session too - otherwise the refresh token would stay valid for a day.
  if (refreshToken) void staffLogout(refreshToken).catch(() => undefined);
}
