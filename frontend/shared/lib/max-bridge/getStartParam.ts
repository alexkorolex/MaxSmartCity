import './types';

/** The value MAX passed through when it opened this page as a mini app (an `open_app`
 * button's `payload`, or a `?startapp=` deep link) - `null` outside MAX or when none was
 * given, in which case callers should fall back to reading it from the URL instead. */
export function getMaxBridgeStartParam(): string | null {
  try {
    return window.WebApp?.initDataUnsafe?.start_param ?? null;
  } catch {
    return null;
  }
}

export function isRunningInsideMax(): boolean {
  return typeof window !== 'undefined' && window.WebApp !== undefined;
}
