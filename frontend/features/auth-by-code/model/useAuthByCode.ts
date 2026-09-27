import { useMutation } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { canSignInWithMaxWebApp, loginByCode, setSession, signInWithMaxWebApp } from '@/entities/session';
import { fetchMyProfile } from '@/entities/user';
import { getMaxBridgeStartParam } from '@/shared/lib';
import { consumeMaxStartRoute, peekMaxStartRoute, ROUTES, safeNextPath } from '@/shared/routes';

export function useAuthByCode() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  // Opened inside MAX (via the bot's `open_app` button): the code travels as the MAX
  // Bridge start_param, not a URL query param. Falls back to `?code=` for the plain
  // browser path (the bot's `link` button, or a manually shared URL).
  const startParam = getMaxBridgeStartParam();
  const code = searchParams.get('code') ?? (peekMaxStartRoute() ? null : startParam);
  const nextPath = safeNextPath(searchParams.get('next'));
  const viaMax = canSignInWithMaxWebApp();
  const attempted = useRef(false);

  const mutation = useMutation({
    mutationFn: async () => {
      if (viaMax && (await signInWithMaxWebApp())) return;
      if (!code) throw new Error('Login code is missing');
      setSession((await loginByCode(code)).token);
    },
    onSuccess: async () => {
      // First-time (or still-unset) residents get prompted for their home right after
      // login; everyone else goes straight in. Best-effort - a failed profile fetch
      // here shouldn't block login, so just fall through to home.
      try {
        const profile = await fetchMyProfile();
        if (!profile.house_id) {
          navigate(ROUTES.selectHouse, { replace: true, state: { mode: 'onboarding' } });
          return;
        }
      } catch {
        /* fall through to home */
      }
      navigate(consumeMaxStartRoute() ?? nextPath ?? ROUTES.home, { replace: true });
    },
  });

  useEffect(() => {
    if ((!code && !viaMax) || attempted.current) return;
    attempted.current = true;
    mutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  return { hasCode: Boolean(code) || viaMax, isPending: mutation.isPending, isError: mutation.isError };
}
