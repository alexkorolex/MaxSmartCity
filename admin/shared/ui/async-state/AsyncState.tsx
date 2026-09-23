import type { ReactNode } from 'react';

import { isApiError } from '@/shared/api';

interface AsyncStateProps {
  isLoading: boolean;
  error: unknown;
  children: ReactNode;
  onRetry?: () => void;
}

function errorMessage(error: unknown): string {
  if (isApiError(error)) return error.message;
  if (error instanceof Error) return error.message;
  return 'Что-то пошло не так';
}

export function AsyncState({ isLoading, error, children, onRetry }: AsyncStateProps) {
  if (isLoading) {
    return (
      <div className="state-block">
        <span className="spinner" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="state-block">
        <span>{errorMessage(error)}</span>
        {onRetry && (
          <button type="button" className="btn btn--ghost btn--small" onClick={onRetry}>
            Повторить
          </button>
        )}
      </div>
    );
  }

  return <>{children}</>;
}
