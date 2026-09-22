import { Flex } from '@maxhub/max-ui';

import { AuthByCodeStatus } from '@/features/auth-by-code';
import { PageLayout } from '@/shared/ui';

export function AuthMaxPage() {
  return (
    <PageLayout title="Вход" withNavSpacing={false}>
      <Flex direction="column" align="center" justify="center" style={{ paddingTop: 48 }}>
        <AuthByCodeStatus />
      </Flex>
    </PageLayout>
  );
}
