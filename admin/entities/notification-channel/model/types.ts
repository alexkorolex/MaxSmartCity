export type ChannelType = 'MAX_MEMBERS' | 'MAX_CHAT' | 'EMAIL' | 'WEBHOOK';

export interface OrganizationChannel {
  id: string;
  organization_id: string;
  type: ChannelType;
  target: string | null;
  is_active: boolean;
  created_at: string;
}

export interface OrganizationChannelPayload {
  organization_id: string;
  type: ChannelType;
  target?: string | null;
  secret?: string | null;
}

export interface ChannelTestResult {
  delivered: boolean;
  error: string | null;
}
