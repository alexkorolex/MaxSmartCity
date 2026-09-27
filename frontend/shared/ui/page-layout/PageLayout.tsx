import { Container, Flex, Typography } from '@maxhub/max-ui';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { ArrowLeftIcon } from '@/shared/ui/icons';

import './PageLayout.css';

interface PageLayoutProps {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  backTo?: string;
  backLabel?: string;
  eyebrow?: string;
  children: ReactNode;
  withNavSpacing?: boolean;
  /** Exactly the viewport's height: the page itself never scrolls, its content does (a chat). */
  fill?: boolean;
}

type PageHeadingProps = Omit<PageLayoutProps, 'children' | 'withNavSpacing' | 'fill'>;

function PageHeading({ title, subtitle, action, backTo, backLabel = 'Назад', eyebrow }: PageHeadingProps) {
  if (!title && !action) return null;

  return (
    <header className="page-heading">
      {backTo && (
        <Link className="page-heading__back" to={backTo} aria-label={backLabel}>
          <ArrowLeftIcon />
          <span className="page-heading__back-label">{backLabel}</span>
        </Link>
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
  const { children, withNavSpacing = true, fill = false, ...heading } = props;

  return (
    <main className={`app-page${withNavSpacing ? ' app-page--with-nav' : ''}${fill ? ' app-page--fill' : ''}`}>
      <Container fullWidth>
        <Flex direction="column" gap="var(--space-4)" className="page-content">
          <PageHeading {...heading} />
          {children}
        </Flex>
      </Container>
    </main>
  );
}
