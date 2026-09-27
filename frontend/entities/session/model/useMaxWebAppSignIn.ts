import { useEffect, useRef, useState } from 'react';

import { canSignInWithMaxWebApp, signInWithMaxWebApp } from './maxWebAppSession';

export function useMaxWebAppSignIn(enabled: boolean): boolean {
  const attempted = useRef(false);
  const [pending, setPending] = useState(() => enabled && canSignInWithMaxWebApp());

  useEffect(() => {
    if (!enabled || attempted.current || !canSignInWithMaxWebApp()) {
      setPending(false);
      return;
    }
    attempted.current = true;
    let active = true;
    setPending(true);
    void signInWithMaxWebApp().finally(() => {
      if (active) setPending(false);
    });
    return () => {
      active = false;
    };
  }, [enabled]);

  return pending;
}
