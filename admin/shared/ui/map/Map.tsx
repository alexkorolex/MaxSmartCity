import * as MapLibreGL from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';
import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState, type ReactNode } from 'react';

import { cn } from '@/shared/lib';

import { MapContext } from './context';
import { useResolvedTheme, type MapTheme } from './useResolvedTheme';

if (!MapLibreGL.getWorkerUrl()) {
  MapLibreGL.setWorkerUrl(maplibreWorkerUrl);
}

const BASEMAP_STYLES: Record<MapTheme, string> = {
  dark: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  light: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
};

export type MapRef = MapLibreGL.Map;

export type MapProps = {
  children?: ReactNode;
  className?: string;
} & Omit<MapLibreGL.MapOptions, 'container' | 'style'>;

function MapLoader() {
  return (
    <div className="bg-background/50 absolute inset-0 z-10 flex items-center justify-center backdrop-blur-xs">
      <div className="flex gap-1">
        <span className="bg-muted-foreground/60 size-1.5 animate-pulse rounded-full" />
        <span className="bg-muted-foreground/60 size-1.5 animate-pulse rounded-full [animation-delay:150ms]" />
        <span className="bg-muted-foreground/60 size-1.5 animate-pulse rounded-full [animation-delay:300ms]" />
      </div>
    </div>
  );
}

export const Map = forwardRef<MapRef, MapProps>(function Map({ children, className, ...options }, ref) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<MapLibreGL.Map | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isStyleLoaded, setIsStyleLoaded] = useState(false);
  const resolvedTheme = useResolvedTheme();
  const appliedThemeRef = useRef(resolvedTheme);
  const initialOptionsRef = useRef(options);

  useImperativeHandle(ref, () => map as MapLibreGL.Map, [map]);

  useEffect(() => {
    if (!containerRef.current) return;
    const instance = new MapLibreGL.Map({
      container: containerRef.current,
      style: BASEMAP_STYLES[appliedThemeRef.current],
      renderWorldCopies: false,
      attributionControl: { compact: true },
      ...initialOptionsRef.current,
    });
    const handleLoad = () => setIsLoaded(true);
    const handleStyleLoad = () => setIsStyleLoaded(true);
    instance.on('load', handleLoad);
    instance.on('style.load', handleStyleLoad);
    setMap(instance);

    return () => {
      instance.off('load', handleLoad);
      instance.off('style.load', handleStyleLoad);
      instance.remove();
      setIsLoaded(false);
      setIsStyleLoaded(false);
      setMap(null);
    };
  }, []);

  useEffect(() => {
    if (!map || appliedThemeRef.current === resolvedTheme) return;
    appliedThemeRef.current = resolvedTheme;
    setIsStyleLoaded(false);
    map.setStyle(BASEMAP_STYLES[resolvedTheme], { diff: false });
  }, [map, resolvedTheme]);

  const contextValue = useMemo(
    () => ({ map, isLoaded: isLoaded && isStyleLoaded, resolvedTheme }),
    [map, isLoaded, isStyleLoaded, resolvedTheme],
  );

  return (
    <MapContext.Provider value={contextValue}>
      <div ref={containerRef} className={cn('relative h-full w-full', className)}>
        {!isLoaded && <MapLoader />}
        {map && children}
      </div>
    </MapContext.Provider>
  );
});
