import type { MaxBridgeWebApp } from './types';

type AvatarSource = Pick<MaxBridgeWebApp, 'initDataUnsafe'>;

function activeBridge(): MaxBridgeWebApp | undefined {
  return typeof window === 'undefined' ? undefined : window.WebApp;
}

/**
 * Returns the current MAX mini-app user's profile photo. MAX documents this value as
 * `initDataUnsafe.user.photo_url`; only HTTPS URLs are accepted before passing it to an
 * image element. The URL is present only while the app is opened inside MAX.
 */
export function getMaxBridgeUserAvatarUrl(source: AvatarSource | null | undefined = activeBridge()): string | null {
  const value = source?.initDataUnsafe.user?.photo_url?.trim();
  if (!value) return null;

  try {
    return new URL(value).protocol === 'https:' ? value : null;
  } catch {
    return null;
  }
}
