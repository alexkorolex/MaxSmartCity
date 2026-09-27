import { setReauthenticateHandler } from '@/shared/api';
import { getMaxBridgeInitData } from '@/shared/lib';

import { loginByMaxWebApp } from '../api/loginByMaxWebApp';
import { setSession } from './tokenStore';

let inflight: Promise<boolean> | null = null;

export function canSignInWithMaxWebApp(): boolean {
  return getMaxBridgeInitData() !== null;
}

export function signInWithMaxWebApp(): Promise<boolean> {
  const initData = getMaxBridgeInitData();
  if (!initData) return Promise.resolve(false);

  inflight ??= loginByMaxWebApp(initData)
    .then((response) => {
      setSession(response.token);
      return true;
    })
    .catch(() => false)
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

setReauthenticateHandler(signInWithMaxWebApp);
