export interface TerritoryStats {
  houses: number;
  houses_without_manager: number;
  managing_organizations: number;
  residents: number;
  reports_total: number;
  reports_open: number;
  reports_last_30_days: number;
  incidents_open: number;
  incidents_critical_open: number;
  incidents_resolved: number;
}

export interface TerritoryRef {
  id: string;
  name: string;
  type: string;
}

export interface TerritoryBreakdown {
  territory: TerritoryRef | null;
  stats: TerritoryStats;
}

export interface TerritorySummary {
  territory: TerritoryRef;
  path: TerritoryRef[];
  total: TerritoryStats;
  children: TerritoryBreakdown[];
  top_categories: { name: string; reports: number }[];
}
