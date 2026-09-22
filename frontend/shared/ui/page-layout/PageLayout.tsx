import { Container, Flex, IconButton, Typography } from '@maxhub/max-ui';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { ArrowLeftIcon } from '@/shared/ui/icons';

interface PageLayoutProps {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  backTo?: string;
  eyebrow?: string;
  children: ReactNode;
  withNavSpacing?: boolean;
}

type PageHeadingProps = Omit<PageLayoutProps, 'children' | 'withNavSpacing'>;

function PageHeading({ title, subtitle, action, backTo, eyebrow }: PageHeadingProps) {
  if (!title && !action) return null;

  return (
    <header className="page-heading">
      {backTo && (
        <IconButton asChild variant="ghost" size="small" aria-label="Назад">
          <Link to={backTo}><ArrowLeftIcon /></Link>
        </IconButton>
      )}
      <div className="page-heading__copy">
        {eyebrow && <span className="page-heading__eyebrow">{eyebrow}</span>}
        {title && (
          <Typography.Text asChild variant="header" color="primary">
            <h1>{title}</h1>
          </Typography.Text>
        )}
        {subtitle && <Typography.Text variant="description" color="secondary">{subtitle}</Typography.Text>}
      </div>
      {action && <div className="page-heading__action">{action}</div>}
    </header>
  );
}

export function PageLayout(props: PageLayoutProps) {
  const { children, withNavSpacing = true } = props;

  return (
    <main className={`app-page${withNavSpacing ? ' app-page--with-nav' : ''}`}>
      <Container fullWidth>
        <Flex direction="column" gap="var(--space-4)" className="page-content">
          <PageHeading {...props} />
          {children}
        </Flex>
      </Container>
    </main>
  );
}
