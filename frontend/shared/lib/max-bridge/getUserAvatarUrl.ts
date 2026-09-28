import type { MaxBridgeWebApp } from './types';

type AvatarSource = Pick<MaxBridgeWebApp, 'initDataUnsafe'>;

function activeBridge(): MaxBridgeWebApp | undefined {
  return typeof window === 'undefined' ? undefined : window.WebApp;
}

export function getMaxBridgeUserAvatarUrl(source: AvatarSource | null | undefined = activeBridge()): string | null {
  const value = source?.initDataUnsafe.user?.photo_url?.trim();
  if (!value) return null;

  try {
    return new URL(value).protocol === 'https:' ? value : null;
  } catch {
    return null;
  }
}
