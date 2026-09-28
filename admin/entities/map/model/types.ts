import type { Feature, FeatureCollection, MultiPolygon, Point, Polygon } from 'geojson';

export interface MapCity {
  city: string;
  houses: number;
  located: number;
  unlocated: number;
  with_footprint: number;
  buildings: number;
  bbox: [number, number, number, number] | null;
}

export interface MapZooms {
  houses_min_zoom: number;
  house_footprints_min_zoom: number;
  buildings_min_zoom: number;
  max_zoom: number;
}

export interface MapScope {
  territory_id: string;
  name: string;
  type: string;
}

export interface MapSummary {
  cities: MapCity[];
  zooms: MapZooms;
  attribution: string[];
  scope: MapScope | null;
}

export interface DistrictProperties {
  district_id: string;
  name: string;
  type: string;
  city: string;
  house_count: number;
  active_reports: number;
  active_incidents: number;
}

export type DistrictCollection = FeatureCollection<Polygon | MultiPolygon, DistrictProperties>;

export interface MapIncident {
  incident_id: string;
  title: string;
  status: string;
  priority: string;
  category: string;
  first_report_at: string | null;
  last_report_at: string | null;
}

export interface IncidentHouseProperties {
  house_id: string;
  address: string;
  incident_count: number;
  incidents: MapIncident[];
}

export type IncidentHouseFeature = Feature<Point, IncidentHouseProperties>;

export interface IncidentHouseCollection extends FeatureCollection<Point, IncidentHouseProperties> {
  metadata: { located_houses: number; unlocated_houses: number };
}

export interface HouseTileProperties {
  house_id: string;
  address?: string;
  has_footprint: boolean;
  active_reports: number;
  active_incidents: number;
}
