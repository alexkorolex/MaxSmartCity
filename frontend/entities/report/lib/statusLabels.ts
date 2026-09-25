import type { StatusTone } from '@/shared/ui';

import type { Priority, ReportStatus } from '../model/types';

export const REPORT_STATUS_LABELS: Record<ReportStatus, string> = {
  RECEIVED: 'Принято',
  PROCESSING: 'В обработке',
  READY_FOR_TRIAGE: 'На рассмотрении',
  LINKED: 'Связано с инцидентом',
  NEEDS_CLARIFICATION: 'Нужны уточнения',
  REJECTED: 'Отклонено',
  WITHDRAWN: 'Отозвано',
  CLOSED: 'Закрыто',
};

export const REPORT_STATUS_TONES: Record<ReportStatus, StatusTone> = {
  RECEIVED: 'neutral',
  PROCESSING: 'info',
  READY_FOR_TRIAGE: 'info',
  LINKED: 'success',
  NEEDS_CLARIFICATION: 'warning',
  REJECTED: 'error',
  WITHDRAWN: 'neutral',
  CLOSED: 'success',
};

export const PRIORITY_LABELS: Record<Priority, string> = {
  LOW: 'Низкая',
  NORMAL: 'Обычная',
  HIGH: 'Высокая',
  CRITICAL: 'Критичная',
};

export const PRIORITY_TONES: Record<Priority, StatusTone> = {
  LOW: 'neutral',
  NORMAL: 'info',
  HIGH: 'warning',
  CRITICAL: 'error',
};
