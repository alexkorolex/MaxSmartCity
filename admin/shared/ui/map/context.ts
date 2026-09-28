import type { Map as MapLibreMap } from 'maplibre-gl';
import { createContext, useContext } from 'react';

import type { MapTheme } from './useResolvedTheme';

export type MapContextValue = {
  map: MapLibreMap | null;
  isLoaded: boolean;
  resolvedTheme: MapTheme;
};

export const MapContext = createContext<MapContextValue | null>(null);

export function useMap(): MapContextValue {
  const context = useContext(MapContext);
  if (!context) {
    throw new Error('useMap must be used within <Map>');
  }
  return context;
}
