import { http } from '@/shared/api';

import type { ChannelTestResult, OrganizationChannel, OrganizationChannelPayload } from '../model/types';

const BASE = '/notifications/organization-channels';

export function fetchOrganizationChannels(organizationId: string): Promise<OrganizationChannel[]> {
  return http.get<OrganizationChannel[]>(`${BASE}/`, { query: { organization_id: organizationId } });
}

export function createOrganizationChannel(payload: OrganizationChannelPayload): Promise<OrganizationChannel> {
  return http.post<OrganizationChannel>(`${BASE}/`, payload);
}

export function setOrganizationChannelActive(channelId: string, active: boolean): Promise<OrganizationChannel> {
  return http.post<OrganizationChannel>(`${BASE}/${channelId}/${active ? 'activate' : 'deactivate'}`);
}

export function deleteOrganizationChannel(channelId: string): Promise<void> {
  return http.delete(`${BASE}/${channelId}`);
}

/** Sends a test message right away, bypassing the delivery queue. */
export function testOrganizationChannel(channelId: string): Promise<ChannelTestResult> {
  return http.post<ChannelTestResult>(`${BASE}/${channelId}/test`);
}
