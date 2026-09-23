import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { createIncidentComment, fetchIncidentComments } from '../api/comments';
import type { IncidentCommentCreatePayload } from './types';

export const incidentCommentsQueryKey = (incidentId?: string) => ['incident-comments', incidentId ?? ''] as const;

export function useIncidentComments(incidentId?: string) {
  return useQuery({
    queryKey: incidentCommentsQueryKey(incidentId),
    queryFn: () => fetchIncidentComments({ incidentId }),
  });
}

export function useCreateIncidentComment(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: IncidentCommentCreatePayload) => createIncidentComment(payload),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: incidentCommentsQueryKey(incidentId) }),
  });
}
