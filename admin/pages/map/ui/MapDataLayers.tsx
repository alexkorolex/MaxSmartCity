import type { FeatureCollection } from 'geojson';
import type { ExpressionSpecification, GeoJSONSource, MapMouseEvent } from 'maplibre-gl';
import { useEffect, useRef } from 'react';

import {
  mapTileUrl,
  type DistrictCollection,
  type DistrictProperties,
  type HouseTileProperties,
  type IncidentHouseCollection,
  type IncidentHouseProperties,
  type MapZooms,
} from '@/entities/map';
import { useMap } from '@/shared/ui/map';

import type { MapLayerVisibility } from '../model/layers';

export type MapSelection =
  | { kind: 'incident'; longitude: number; latitude: number; properties: IncidentHouseProperties }
  | { kind: 'house'; longitude: number; latitude: number; properties: HouseTileProperties }
  | { kind: 'district'; longitude: number; latitude: number; properties: DistrictProperties };

const SOURCES = {
  buildings: 'sc-buildings',
  houses: 'sc-houses',
  districts: 'sc-districts',
  incidents: 'sc-incidents',
} as const;

const LAYERS = {
  buildings: 'sc-buildings-fill',
  citiesFill: 'sc-cities-fill',
  districtsFill: 'sc-districts-fill',
  districtsLine: 'sc-districts-line',
  citiesLine: 'sc-cities-line',
  housesFill: 'sc-houses-fill',
  housesLine: 'sc-houses-line',
  housesPoint: 'sc-houses-point',
  incidentsHalo: 'sc-incidents-halo',
  incidentsPoint: 'sc-incidents-point',
} as const;

const VISIBILITY_GROUPS: Record<keyof MapLayerVisibility, string[]> = {
  buildings: [LAYERS.buildings],
  districts: [LAYERS.citiesFill, LAYERS.districtsFill, LAYERS.districtsLine, LAYERS.citiesLine],
  houses: [LAYERS.housesFill, LAYERS.housesLine, LAYERS.housesPoint],
  incidents: [LAYERS.incidentsHalo, LAYERS.incidentsPoint],
};

export const MAP_COLORS = {
  calm: '#1B8FBF',
  reports: '#E69822',
  incident: '#D92D4B',
} as const;

const THEME_COLORS = {
  light: { building: '#8C9BA2', districtLine: '#2F5F72', districtFill: '#1B8FBF', halo: '#FFFFFF' },
  dark: { building: '#6D8791', districtLine: '#8FD4EA', districtFill: '#24BCE5', halo: '#0B1A20' },
} as const;

const HOUSE_COLOR: ExpressionSpecification = [
  'case',
  ['>', ['get', 'active_incidents'], 0],
  MAP_COLORS.incident,
  ['>', ['get', 'active_reports'], 0],
  MAP_COLORS.reports,
  MAP_COLORS.calm,
];

const IS_CITY: ExpressionSpecification = ['==', ['get', 'type'], 'CITY'];

const EMPTY_COLLECTION: FeatureCollection = { type: 'FeatureCollection', features: [] };

interface MapDataLayersProps {
  zooms: MapZooms;
  districts: DistrictCollection | undefined;
  incidents: IncidentHouseCollection | undefined;
  visibility: MapLayerVisibility;
  onSelect: (selection: MapSelection | null) => void;
}

export function MapDataLayers({ zooms, districts, incidents, visibility, onSelect }: MapDataLayersProps) {
  const { map, isLoaded, resolvedTheme } = useMap();
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!map || !isLoaded) return undefined;
    const colors = THEME_COLORS[resolvedTheme];

    if (!map.getSource(SOURCES.buildings)) {
      map.addSource(SOURCES.buildings, {
        type: 'vector',
        tiles: [mapTileUrl('buildings')],
        minzoom: zooms.buildings_min_zoom,
        maxzoom: 16,
      });
    }
    if (!map.getSource(SOURCES.districts)) {
      map.addSource(SOURCES.districts, { type: 'geojson', data: EMPTY_COLLECTION, promoteId: 'district_id' });
    }
    if (!map.getSource(SOURCES.houses)) {
      map.addSource(SOURCES.houses, {
        type: 'vector',
        tiles: [mapTileUrl('houses')],
        minzoom: zooms.houses_min_zoom,
        maxzoom: 17,
        promoteId: { houses: 'house_id' },
      });
    }
    if (!map.getSource(SOURCES.incidents)) {
      map.addSource(SOURCES.incidents, { type: 'geojson', data: EMPTY_COLLECTION });
    }

    const add = (layer: Parameters<typeof map.addLayer>[0]) => {
      if (!map.getLayer(layer.id)) map.addLayer(layer);
    };
    add({
      id: LAYERS.buildings,
      type: 'fill',
      source: SOURCES.buildings,
      'source-layer': 'buildings',
      minzoom: zooms.buildings_min_zoom,
      paint: { 'fill-color': colors.building, 'fill-opacity': 0.22 },
    });
    add({
      id: LAYERS.citiesFill,
      type: 'fill',
      source: SOURCES.districts,
      filter: IS_CITY,
      paint: {
        'fill-color': colors.districtFill,
        'fill-opacity': ['interpolate', ['linear'], ['get', 'active_incidents'], 0, 0.02, 5, 0.1, 20, 0.2],
      },
    });
    add({
      id: LAYERS.districtsFill,
      type: 'fill',
      source: SOURCES.districts,
      filter: ['!', IS_CITY],
      paint: {
        'fill-color': colors.districtFill,
        'fill-opacity': [
          'interpolate',
          ['linear'],
          ['get', 'active_incidents'],
          0,
          0.04,
          5,
          0.16,
          20,
          0.3,
        ],
      },
    });
    add({
      id: LAYERS.districtsLine,
      type: 'line',
      source: SOURCES.districts,
      filter: ['!', IS_CITY],
      paint: { 'line-color': colors.districtLine, 'line-width': 1.6, 'line-opacity': 0.75 },
    });
    add({
      id: LAYERS.citiesLine,
      type: 'line',
      source: SOURCES.districts,
      filter: IS_CITY,
      paint: {
        'line-color': colors.districtLine,
        'line-width': 2.4,
        'line-opacity': 0.9,
        'line-dasharray': [3, 2],
      },
    });
    add({
      id: LAYERS.housesFill,
      type: 'fill',
      source: SOURCES.houses,
      'source-layer': 'houses',
      filter: ['==', ['geometry-type'], 'Polygon'],
      paint: { 'fill-color': HOUSE_COLOR, 'fill-opacity': 0.55 },
    });
    add({
      id: LAYERS.housesLine,
      type: 'line',
      source: SOURCES.houses,
      'source-layer': 'houses',
      filter: ['==', ['geometry-type'], 'Polygon'],
      paint: { 'line-color': HOUSE_COLOR, 'line-width': 1 },
    });
    add({
      id: LAYERS.housesPoint,
      type: 'circle',
      source: SOURCES.houses,
      'source-layer': 'houses',
      filter: ['==', ['geometry-type'], 'Point'],
      paint: {
        'circle-color': HOUSE_COLOR,
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 12, 1.8, 15, 3.5, 17, 5],
        'circle-opacity': 0.85,
      },
    });
    add({
      id: LAYERS.incidentsHalo,
      type: 'circle',
      source: SOURCES.incidents,
      paint: {
        'circle-color': MAP_COLORS.incident,
        'circle-opacity': 0.18,
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 10, 14, 18, 17, 26],
      },
    });
    add({
      id: LAYERS.incidentsPoint,
      type: 'circle',
      source: SOURCES.incidents,
      paint: {
        'circle-color': MAP_COLORS.incident,
        'circle-radius': [
          'interpolate',
          ['linear'],
          ['zoom'],
          9,
          ['+', 4, ['min', ['get', 'incident_count'], 4]],
          16,
          ['+', 7, ['min', ['get', 'incident_count'], 6]],
        ],
        'circle-stroke-color': colors.halo,
        'circle-stroke-width': 2,
      },
    });

    const interactive = [
      LAYERS.incidentsPoint,
      LAYERS.housesFill,
      LAYERS.housesPoint,
      LAYERS.districtsFill,
      LAYERS.citiesFill,
    ];
    const handleClick = (event: MapMouseEvent) => {
      const layers = interactive.filter((id) => map.getLayer(id));
      const [feature] = map.queryRenderedFeatures(event.point, { layers });
      if (!feature) {
        onSelectRef.current(null);
        return;
      }
      const { lng: longitude, lat: latitude } = event.lngLat;
      if (feature.layer.id === LAYERS.incidentsPoint) {
        const properties = feature.properties as Record<string, unknown>;
        const incidentsValue = properties.incidents;
        onSelectRef.current({
          kind: 'incident',
          longitude,
          latitude,
          properties: {
            ...(properties as unknown as IncidentHouseProperties),
            incidents: typeof incidentsValue === 'string' ? JSON.parse(incidentsValue) : incidentsValue,
          },
        });
      } else if (feature.layer.id === LAYERS.districtsFill || feature.layer.id === LAYERS.citiesFill) {
        onSelectRef.current({
          kind: 'district',
          longitude,
          latitude,
          properties: feature.properties as unknown as DistrictProperties,
        });
      } else {
        onSelectRef.current({
          kind: 'house',
          longitude,
          latitude,
          properties: feature.properties as unknown as HouseTileProperties,
        });
      }
    };
    const setPointer = () => {
      map.getCanvas().style.cursor = 'pointer';
    };
    const resetPointer = () => {
      map.getCanvas().style.cursor = '';
    };
    map.on('click', handleClick);
    for (const layer of interactive) {
      map.on('mouseenter', layer, setPointer);
      map.on('mouseleave', layer, resetPointer);
    }
    return () => {
      map.off('click', handleClick);
      for (const layer of interactive) {
        map.off('mouseenter', layer, setPointer);
        map.off('mouseleave', layer, resetPointer);
      }
    };
  }, [map, isLoaded, resolvedTheme, zooms]);

  useEffect(() => {
    if (!map || !isLoaded) return;
    const source = map.getSource<GeoJSONSource>(SOURCES.districts);
    source?.setData(districts ?? EMPTY_COLLECTION);
  }, [map, isLoaded, districts]);

  useEffect(() => {
    if (!map || !isLoaded) return;
    const source = map.getSource<GeoJSONSource>(SOURCES.incidents);
    source?.setData(incidents ?? EMPTY_COLLECTION);
  }, [map, isLoaded, incidents]);

  useEffect(() => {
    if (!map || !isLoaded) return;
    for (const [group, layerIds] of Object.entries(VISIBILITY_GROUPS)) {
      const value = visibility[group as keyof MapLayerVisibility] ? 'visible' : 'none';
      for (const id of layerIds) {
        if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', value);
      }
    }
  }, [map, isLoaded, visibility, resolvedTheme]);

  return null;
}
