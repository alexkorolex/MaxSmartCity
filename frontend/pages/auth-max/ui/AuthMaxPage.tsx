import { Flex } from '@maxhub/max-ui';

import { AuthByCodeStatus } from '@/features/auth-by-code';
import { PageLayout } from '@/shared/ui';

import './AuthMaxPage.css';

export function AuthMaxPage() {
  return (
    <PageLayout withNavSpacing={false}>
      <Flex className="auth-max-page__stage" direction="column" align="center" justify="center" gap="var(--space-4)">
        <AuthByCodeStatus />
      </Flex>
    </PageLayout>
  );
}
