import type { RequestParameters } from 'maplibre-gl';
import { useCallback, useMemo, useRef, useState } from 'react';

import { isMapApiUrl, useIncidentHouses, useMapDistricts, useMapSummary, type MapCity } from '@/entities/map';
import { isAdmin, isAuthority, useMe } from '@/entities/session';
import { getAuthToken } from '@/shared/api';
import { cn } from '@/shared/lib';
import { AsyncState, EmptyState, MapIcon } from '@/shared/ui';
import { Map, MapControls, type MapRef } from '@/shared/ui/map';

import { useLayerVisibility, type MapLayerVisibility } from '../model/layers';
import { useKeepTokenFresh } from '../model/useKeepTokenFresh';
import { MAP_COLORS, MapDataLayers, type MapSelection } from './MapDataLayers';
import { MapSelectionPopup } from './MapSelectionPopup';

const LAYER_OPTIONS: { key: keyof MapLayerVisibility; label: string; hint: string }[] = [
  { key: 'incidents', label: 'Инциденты', hint: 'дома с активными инцидентами, на любом масштабе' },
  { key: 'districts', label: 'Районы', hint: 'чем больше инцидентов, тем насыщеннее заливка' },
  { key: 'houses', label: 'Дома', hint: 'точки с 12 зума, контуры с 15' },
  { key: 'buildings', label: 'Застройка', hint: 'все здания без адресов, с 14 зума' },
];

const LEGEND = [
  { color: MAP_COLORS.incident, label: 'Есть инцидент' },
  { color: MAP_COLORS.reports, label: 'Есть заявки' },
  { color: MAP_COLORS.calm, label: 'Без обращений' },
];

function withMapAuth(url: string): RequestParameters {
  const token = getAuthToken();
  return isMapApiUrl(url) && token ? { url, headers: { Authorization: `Bearer ${token}` } } : { url };
}

function coverage(city: MapCity): string {
  const percent = city.houses ? Math.round((city.located / city.houses) * 100) : 0;
  return `${city.located.toLocaleString('ru-RU')} из ${city.houses.toLocaleString('ru-RU')} домов (${percent}%)`;
}

export function MapPage() {
  const { data: principal } = useMe();
  const allowed = isAdmin(principal) || isAuthority(principal);
  const summary = useMapSummary();
  const districts = useMapDistricts();
  const [includeClosed, setIncludeClosed] = useState(false);
  const incidents = useIncidentHouses(includeClosed);
  const [visibility, toggleLayer] = useLayerVisibility();
  const [selection, setSelection] = useState<MapSelection | null>(null);
  const mapRef = useRef<MapRef>(null);
  useKeepTokenFresh();

  const cities = summary.data?.cities.filter((city) => city.bbox) ?? [];
  const initialBounds = cities[0]?.bbox ?? undefined;
  const attribution = useMemo(() => summary.data?.attribution ?? [], [summary.data]);

  const flyTo = useCallback((city: MapCity) => {
    if (city.bbox) mapRef.current?.fitBounds(city.bbox, { padding: 40, duration: 900 });
  }, []);

  if (principal && !allowed) {
    return <EmptyState icon={<MapIcon />} title="Карта доступна администраторам и органам власти" />;
  }

  return (
    <AsyncState isLoading={summary.isLoading} error={summary.error} onRetry={() => void summary.refetch()}>
      {summary.data && (
        <div className="admin-map relative h-[calc(100dvh-var(--topbar-height)-64px)] min-h-[520px] overflow-hidden rounded-2xl border border-border">
          <Map
            ref={mapRef}
            bounds={initialBounds}
            fitBoundsOptions={{ padding: 40 }}
            maxZoom={summary.data.zooms.max_zoom}
            transformRequest={withMapAuth}
            attributionControl={{ compact: true, customAttribution: attribution }}
          >
            <MapControls position="bottom-right" showZoom showCompass showFullscreen />
            <MapDataLayers
              zooms={summary.data.zooms}
              districts={districts.data}
              incidents={incidents.data}
              visibility={visibility}
              onSelect={setSelection}
            />
            {selection && <MapSelectionPopup selection={selection} onClose={() => setSelection(null)} />}
          </Map>

          <aside className="absolute top-3 left-3 z-10 flex w-72 max-w-[calc(100%-24px)] flex-col gap-3 rounded-xl border border-border bg-popover/95 p-3 text-sm text-popover-foreground shadow-md backdrop-blur">
            <div>
              <div className="text-base font-semibold">Карта</div>
              {summary.data.scope && (
                <div className="text-xs font-medium text-primary">Территория: {summary.data.scope.name}</div>
              )}
              <div className="text-xs text-muted-foreground">
                Инцидентов на карте: {incidents.data?.features.length ?? 0}
                {incidents.data?.metadata.unlocated_houses
                  ? `, ещё ${incidents.data.metadata.unlocated_houses} без координат дома`
                  : ''}
              </div>
            </div>

            {cities.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {cities.map((city) => (
                  <button
                    key={city.city}
                    type="button"
                    className="rounded-md border border-border px-2 py-1 hover:bg-accent"
                    onClick={() => flyTo(city)}
                    title={`Координаты есть у ${coverage(city)}`}
                  >
                    {city.city}
                  </button>
                ))}
              </div>
            )}

            <div className="flex flex-col gap-2">
              {LAYER_OPTIONS.map((option) => (
                <label key={option.key} className="flex cursor-pointer items-start gap-2">
                  <input
                    type="checkbox"
                    className="mt-0.5"
                    checked={visibility[option.key]}
                    onChange={() => toggleLayer(option.key)}
                  />
                  <span>
                    <span className="font-medium">{option.label}</span>
                    <span className="block text-xs text-muted-foreground">{option.hint}</span>
                  </span>
                </label>
              ))}
              <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
                <input type="checkbox" checked={includeClosed} onChange={() => setIncludeClosed(!includeClosed)} />
                Показывать и закрытые инциденты
              </label>
            </div>

            <div className="flex flex-col gap-1 border-t border-border pt-2 text-xs">
              {LEGEND.map((item) => (
                <div key={item.label} className="flex items-center gap-2">
                  <span className="size-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                  {item.label}
                </div>
              ))}
            </div>

            {cities.map((city) => (
              <div key={city.city} className={cn('text-xs text-muted-foreground')}>
                {city.city}: координаты у {coverage(city)}
              </div>
            ))}
          </aside>
        </div>
      )}
    </AsyncState>
  );
}
