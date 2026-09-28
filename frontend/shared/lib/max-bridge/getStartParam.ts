import './types';

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
