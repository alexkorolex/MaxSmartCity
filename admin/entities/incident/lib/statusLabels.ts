import type { PillTone } from '@/shared/ui';

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

export const INCIDENT_STATUS_TONES: Record<IncidentStatus, PillTone> = {
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

/** Statuses in which staff can report the work as done (mirrors the backend's
 * `STAFF_COMPLETABLE_STATUSES`). */
export const COMPLETABLE_INCIDENT_STATUSES: ReadonlySet<IncidentStatus> = new Set<IncidentStatus>([
  'NEW',
  'TRIAGE',
  'CONFIRMED',
  'ASSIGNED',
  'IN_PROGRESS',
  'REOPENED',
  'RESOLUTION_DISPUTED',
]);
