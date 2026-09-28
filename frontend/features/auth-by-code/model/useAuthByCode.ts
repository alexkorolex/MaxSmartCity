import { useMutation } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { canSignInWithMaxWebApp, loginByCode, setSession, signInWithMaxWebApp } from '@/entities/session';
import { fetchMyProfile } from '@/entities/user';
import { getMaxBridgeStartParam } from '@/shared/lib';
import { consumeMaxStartRoute, peekMaxStartRoute, ROUTES, safeNextPath } from '@/shared/routes';

function readLinkParams(): URLSearchParams {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const query = new URLSearchParams(window.location.search);
  for (const key of ['code', 'next']) {
    const value = query.get(key);
    if (!params.has(key) && value !== null) params.set(key, value);
  }
  return params;
}

function stripLinkParams(): void {
  if (window.location.hash || window.location.search) {
    window.history.replaceState(window.history.state, '', window.location.pathname);
  }
}

export function useAuthByCode() {
  const [linkParams] = useState(readLinkParams);
  const navigate = useNavigate();
  const startParam = getMaxBridgeStartParam();
  const code = linkParams.get('code') ?? (peekMaxStartRoute() ? null : startParam);
  const nextPath = safeNextPath(linkParams.get('next'));
  const viaMax = canSignInWithMaxWebApp();
  const attempted = useRef(false);

  const mutation = useMutation({
    mutationFn: async () => {
      if (viaMax && (await signInWithMaxWebApp())) return;
      if (!code) throw new Error('Login code is missing');
      setSession((await loginByCode(code)).token);
    },
    onSuccess: async () => {
      try {
        const profile = await fetchMyProfile();
        if (!profile.house_id) {
          navigate(ROUTES.selectHouse, { replace: true, state: { mode: 'onboarding' } });
          return;
        }
      } catch {}
      navigate(consumeMaxStartRoute() ?? nextPath ?? ROUTES.home, { replace: true });
    },
  });

  useEffect(() => {
    stripLinkParams();
    if ((!code && !viaMax) || attempted.current) return;
    attempted.current = true;
    mutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  return { hasCode: Boolean(code) || viaMax, isPending: mutation.isPending, isError: mutation.isError };
}
