import { http } from '@/shared/api';

import type { IncidentComment, IncidentCommentCreatePayload } from '../model/types';

interface ListParams {
  incidentId?: string;
  limit?: number;
  offset?: number;
}

export function fetchIncidentComments(params: ListParams = {}): Promise<IncidentComment[]> {
  return http.get<IncidentComment[]>('/collaboration/incident-comments/', {
    query: {
      incident_id: params.incidentId,
      limit: params.limit ?? 100,
      offset: params.offset,
    },
  });
}

export function createIncidentComment(payload: IncidentCommentCreatePayload): Promise<IncidentComment> {
  return http.post<IncidentComment>('/collaboration/incident-comments/', payload);
}
