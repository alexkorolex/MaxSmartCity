import { Flex, Typography } from '@maxhub/max-ui';
import type { ReactNode } from 'react';

import './EmptyState.css';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <Flex className="empty-state" direction="column" align="center" gap={12}>
      {icon && (
        <Flex
          align="center"
          justify="center"
          className="empty-state__icon"
        >
          {icon}
        </Flex>
      )}
      <Flex direction="column" align="center" gap={4}>
        <Typography.Text variant="body-strong" color="primary">
          {title}
        </Typography.Text>
        {description && (
          <Typography.Text className="empty-state__description" variant="description" color="secondary">
            {description}
          </Typography.Text>
        )}
      </Flex>
      {action}
    </Flex>
  );
}
