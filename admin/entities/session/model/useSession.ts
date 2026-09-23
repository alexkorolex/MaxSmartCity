import { useSyncExternalStore } from 'react';

import { getToken, subscribe } from './tokenStore';

export function useSession(): { isAuthenticated: boolean; token: string | null } {
  const token = useSyncExternalStore(subscribe, getToken);
  return { isAuthenticated: token !== null, token };
}
