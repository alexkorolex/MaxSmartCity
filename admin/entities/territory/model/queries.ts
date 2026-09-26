import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import {
  assignToTerritory,
  createTerritory,
  deleteTerritory,
  fetchTerritories,
  fetchTerritoryStreetHouses,
  fetchTerritoryStreets,
  updateTerritory,
} from '../api/territories';
import type { TerritoryAssignPayload, TerritoryCreatePayload, TerritoryNode, TerritoryUpdatePayload } from './types';

export const territoriesQueryKey = ['territories'] as const;

export function useTerritories(enabled = true) {
  return useQuery({ queryKey: territoriesQueryKey, queryFn: fetchTerritories, enabled });
}

export function useTerritoryStreets(territoryId: string | null, q: string) {
  return useQuery({
    queryKey: [...territoriesQueryKey, territoryId, 'streets', q],
    queryFn: () => fetchTerritoryStreets(territoryId ?? '', q),
    enabled: Boolean(territoryId),
    placeholderData: keepPreviousData,
  });
}

export function useTerritoryStreetHouses(territoryId: string | null, street: string | null) {
  return useQuery({
    queryKey: [...territoriesQueryKey, territoryId, 'houses', street],
    queryFn: () => fetchTerritoryStreetHouses(territoryId ?? '', street ?? ''),
    enabled: Boolean(territoryId && street),
  });
}

function useTreeMutation<Variables>(mutationFn: (variables: Variables) => Promise<TerritoryNode[] | void>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: (tree) => {
      if (tree) queryClient.setQueryData(territoriesQueryKey, tree);
      void queryClient.invalidateQueries({ queryKey: territoriesQueryKey });
    },
  });
}

export function useCreateTerritory() {
  return useTreeMutation((payload: TerritoryCreatePayload) => createTerritory(payload));
}

export function useUpdateTerritory() {
  return useTreeMutation(({ id, payload }: { id: string; payload: TerritoryUpdatePayload }) =>
    updateTerritory(id, payload),
  );
}

export function useDeleteTerritory() {
  return useTreeMutation((id: string) => deleteTerritory(id));
}

export function useAssignToTerritory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: TerritoryAssignPayload }) => assignToTerritory(id, payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: territoriesQueryKey });
      void queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}
