import type { MaxBridgeWebApp } from './types';

type InitDataSource = Pick<MaxBridgeWebApp, 'initData'>;

function activeBridge(): MaxBridgeWebApp | undefined {
  return typeof window === 'undefined' ? undefined : window.WebApp;
}

export function getMaxBridgeInitData(source: InitDataSource | null | undefined = activeBridge()): string | null {
  try {
    const value = source?.initData?.trim();
    return value ? value : null;
  } catch {
    return null;
  }
}
