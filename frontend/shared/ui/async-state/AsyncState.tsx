import { Button, Flex, Spinner, Typography } from '@maxhub/max-ui';
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
      <Flex justify="center" align="center" style={{ padding: '48px 0' }}>
        <Spinner size={24} appearance="primary" />
      </Flex>
    );
  }

  if (error) {
    return (
      <Flex direction="column" align="center" gap={12} style={{ padding: '40px 24px', textAlign: 'center' }}>
        <Typography.Text variant="body" color="secondary">
          {errorMessage(error)}
        </Typography.Text>
        {onRetry && (
          <Button variant="secondary" size="small" onClick={onRetry}>
            Повторить
          </Button>
        )}
      </Flex>
    );
  }

  return <>{children}</>;
}
