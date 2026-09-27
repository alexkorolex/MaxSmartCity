import { Flex, Spinner, Typography } from '@maxhub/max-ui';

import { EmptyState, WarningIcon } from '@/shared/ui';

import { useAuthByCode } from '../model/useAuthByCode';

export function AuthByCodeStatus() {
  const { hasCode, isPending, isError } = useAuthByCode();

  if (!hasCode) {
    return (
      <EmptyState
        icon={<WarningIcon width={28} height={28} />}
        title="Ссылка неполная"
        description="Код входа не найден. Вернитесь в бота MAX и попробуйте снова."
      />
    );
  }

  if (isError) {
    return (
      <EmptyState
        icon={<WarningIcon width={28} height={28} />}
        title="Ссылка устарела"
        description="Она уже использована или истекла. Вернитесь в бота MAX и отправьте /start."
      />
    );
  }

  return (
    <Flex direction="column" align="center" gap="var(--space-3)">
      <Spinner size={24} appearance="primary" />
      <Typography.Text variant="body" color="secondary">
        {isPending ? 'Выполняем вход…' : 'Секунду…'}
      </Typography.Text>
    </Flex>
  );
}
