import type { TerritoryNode, TerritoryType } from '../model/types';

export const TERRITORY_TYPE_LABELS: Record<TerritoryType, string> = {
  CITY: 'Город',
  ADMINISTRATIVE_OKRUG: 'Административный округ',
  DISTRICT: 'Район',
  MUNICIPALITY: 'Муниципальное образование',
  SETTLEMENT: 'Посёлок',
  OTHER: 'Другое деление',
};

export const CHILD_TERRITORY_TYPES: TerritoryType[] = [
  'DISTRICT',
  'ADMINISTRATIVE_OKRUG',
  'MUNICIPALITY',
  'SETTLEMENT',
  'OTHER',
];

export interface TerritoryTreeItem {
  node: TerritoryNode;
  depth: number;
  hasChildren: boolean;
}

export function flattenTerritoryTree(nodes: TerritoryNode[]): TerritoryTreeItem[] {
  const children = new Map<string | null, TerritoryNode[]>();
  const ids = new Set(nodes.map((node) => node.id));
  for (const node of nodes) {
    const parent = node.parent_id && ids.has(node.parent_id) ? node.parent_id : null;
    children.set(parent, [...(children.get(parent) ?? []), node]);
  }
  const result: TerritoryTreeItem[] = [];
  const visit = (parent: string | null, depth: number) => {
    const level = [...(children.get(parent) ?? [])].sort((a, b) => a.name.localeCompare(b.name, 'ru'));
    for (const node of level) {
      result.push({ node, depth, hasChildren: children.has(node.id) });
      visit(node.id, depth + 1);
    }
  };
  visit(null, 0);
  return result;
}

export function territoryPath(nodes: TerritoryNode[], id: string): TerritoryNode[] {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const path: TerritoryNode[] = [];
  let current = byId.get(id);
  while (current) {
    path.unshift(current);
    current = current.parent_id ? byId.get(current.parent_id) : undefined;
  }
  return path;
}
