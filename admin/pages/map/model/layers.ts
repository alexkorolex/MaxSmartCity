import { useCallback, useState } from 'react';

export interface MapLayerVisibility {
  districts: boolean;
  incidents: boolean;
  houses: boolean;
  buildings: boolean;
}

const STORAGE_KEY = 'maxsc-admin.map-layers';
const DEFAULT_VISIBILITY: MapLayerVisibility = { districts: true, incidents: true, houses: true, buildings: true };

function readVisibility(): MapLayerVisibility {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored ? { ...DEFAULT_VISIBILITY, ...(JSON.parse(stored) as Partial<MapLayerVisibility>) } : DEFAULT_VISIBILITY;
  } catch {
    return DEFAULT_VISIBILITY;
  }
}

export function useLayerVisibility(): [MapLayerVisibility, (layer: keyof MapLayerVisibility) => void] {
  const [visibility, setVisibility] = useState(readVisibility);
  const toggle = useCallback((layer: keyof MapLayerVisibility) => {
    setVisibility((current) => {
      const next = { ...current, [layer]: !current[layer] };
      try {
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* the choice just won't survive a reload */
      }
      return next;
    });
  }, []);
  return [visibility, toggle];
}
