import { Container, Flex, Typography } from '@maxhub/max-ui';
import type { ReactNode } from 'react';

interface PageLayoutProps {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  /** Reserves space at the bottom so content isn't hidden behind the bottom nav bar.
   * Turn off for pages rendered without the nav widget (e.g. the auth callback page). */
  withNavSpacing?: boolean;
}

export function PageLayout({ title, action, children, withNavSpacing = true }: PageLayoutProps) {
  return (
    <Container fullWidth>
      <Flex
        direction="column"
        gap={16}
        style={{
          paddingTop: 16,
          paddingBottom: withNavSpacing ? 'calc(var(--bottom-nav-height) + 16px)' : 16,
        }}
      >
        {title && (
          <Flex justify="space-between" align="center">
            <Typography.Text variant="header" color="primary">
              {title}
            </Typography.Text>
            {action}
          </Flex>
        )}
        {children}
      </Flex>
    </Container>
  );
}
