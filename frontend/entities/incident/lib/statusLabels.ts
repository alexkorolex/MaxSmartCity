import type { StatusTone } from '@/shared/ui';

import type { IncidentStatus } from '../model/types';

export const INCIDENT_STATUS_LABELS: Record<IncidentStatus, string> = {
  NEW: 'Новый',
  TRIAGE: 'На рассмотрении',
  CONFIRMED: 'Подтверждён',
  ASSIGNED: 'Назначен исполнитель',
  IN_PROGRESS: 'В работе',
  RESOLVED: 'Решён',
  AWAITING_CONFIRMATION: 'Ожидает подтверждения',
  CLOSED: 'Закрыт',
  REJECTED: 'Отклонён',
  CANCELLED: 'Отменён',
  MERGED: 'Объединён с другим',
  RESOLUTION_DISPUTED: 'Решение оспорено',
  REOPENED: 'Возобновлён',
};

export const INCIDENT_STATUS_TONES: Record<IncidentStatus, StatusTone> = {
  NEW: 'neutral',
  TRIAGE: 'info',
  CONFIRMED: 'info',
  ASSIGNED: 'info',
  IN_PROGRESS: 'info',
  RESOLVED: 'success',
  AWAITING_CONFIRMATION: 'warning',
  CLOSED: 'success',
  REJECTED: 'error',
  CANCELLED: 'neutral',
  MERGED: 'neutral',
  RESOLUTION_DISPUTED: 'error',
  REOPENED: 'warning',
};

export function canConfirmOrDispute(status: IncidentStatus): boolean {
  return status === 'AWAITING_CONFIRMATION';
}
