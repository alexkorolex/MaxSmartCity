import { useEffect } from 'react';

import { getAuthToken, refreshAuthToken } from '@/shared/api';
import { tokenExpiresAt } from '@/shared/lib';

const REFRESH_BEFORE_MS = 30_000;
const MIN_DELAY_MS = 5_000;

export function useKeepTokenFresh(): void {
  useEffect(() => {
    let timer: number | undefined;
    let cancelled = false;

    const schedule = () => {
      const expiresAt = tokenExpiresAt(getAuthToken());
      if (expiresAt === null || cancelled) return;
      const delay = Math.max(expiresAt - Date.now() - REFRESH_BEFORE_MS, MIN_DELAY_MS);
      timer = window.setTimeout(() => {
        void refreshAuthToken().then((renewed) => {
          if (renewed) schedule();
        });
      }, delay);
    };

    schedule();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);
}
