import { getMaxBridgeStartParam } from '@/shared/lib';

import { routeFromStartParam } from './startParam';

let consumed = false;

export function peekMaxStartRoute(): string | null {
  return consumed ? null : routeFromStartParam(getMaxBridgeStartParam());
}

export function consumeMaxStartRoute(): string | null {
  const route = peekMaxStartRoute();
  consumed = true;
  return route;
}
