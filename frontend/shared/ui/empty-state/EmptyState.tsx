import { Flex, Typography } from '@maxhub/max-ui';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <Flex direction="column" align="center" gap={8}>
      <Typography.Text variant="body-strong" color="primary">
        {title}
      </Typography.Text>
      {description && (
        <Typography.Text variant="description" color="secondary">
          {description}
        </Typography.Text>
      )}
      {action}
    </Flex>
  );
}
