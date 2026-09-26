export {
  territoriesQueryKey,
  useAssignToTerritory,
  useCreateTerritory,
  useDeleteTerritory,
  useTerritories,
  useTerritoryStreetHouses,
  useTerritoryStreets,
  useUpdateTerritory,
} from './model/queries';
export type {
  TerritoryHouse,
  TerritoryNode,
  TerritoryStreet,
  TerritoryStreetShare,
  TerritoryType,
} from './model/types';
export {
  CHILD_TERRITORY_TYPES,
  flattenTerritoryTree,
  TERRITORY_TYPE_LABELS,
  territoryPath,
  type TerritoryTreeItem,
} from './lib/tree';
