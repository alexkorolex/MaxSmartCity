import { isApiError } from '@/shared/api';

export function apiErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    if (error.status === 403) return 'Недостаточно прав для этого действия';
    if (error.status === 502) return 'Сервис учётных записей недоступен, попробуйте позже';
    return error.message;
  }
  if (error instanceof Error) return error.message;
  return 'Что-то пошло не так';
}
