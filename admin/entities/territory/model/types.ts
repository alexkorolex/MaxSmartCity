export type TerritoryType = 'CITY' | 'ADMINISTRATIVE_OKRUG' | 'DISTRICT' | 'MUNICIPALITY' | 'SETTLEMENT' | 'OTHER';

export interface TerritoryNode {
  id: string;
  parent_id: string | null;
  name: string;
  type: TerritoryType;
  direct_house_count: number;
  house_count: number;
  authorities: string[];
}

export interface TerritoryStreetShare {
  territory_id: string;
  territory_name: string;
  house_count: number;
}

export interface TerritoryStreet {
  street: string;
  house_count: number;
  territories: TerritoryStreetShare[];
}

export interface TerritoryHouse {
  house_id: string;
  formatted: string;
  house_number: string | null;
  territory_id: string;
  territory_name: string;
}

export interface TerritoryCreatePayload {
  name: string;
  type: TerritoryType;
  parent_id?: string | null;
}

export interface TerritoryUpdatePayload {
  name?: string;
  type?: TerritoryType;
  parent_id?: string;
}

export interface TerritoryAssignPayload {
  streets?: string[];
  house_ids?: string[];
}
