import { Flex, Spinner, Typography } from '@maxhub/max-ui';

import { useAuthByCode } from '../model/useAuthByCode';

export function AuthByCodeStatus() {
  const { hasCode, isPending, isError } = useAuthByCode();

  if (!hasCode) {
    return (
      <Typography.Text variant="body" color="secondary">
        Ссылка неполная — код входа не найден. Вернитесь в бота MAX и попробуйте снова.
      </Typography.Text>
    );
  }

  if (isError) {
    return (
      <Typography.Text variant="body" color="secondary">
        Ссылка для входа устарела или уже использована. Вернитесь в бота MAX и запросите новую командой /login.
      </Typography.Text>
    );
  }

  return (
    <Flex direction="column" align="center" gap={12}>
      <Spinner size={24} appearance="primary" />
      <Typography.Text variant="body" color="secondary">
        {isPending ? 'Выполняем вход…' : 'Секунду…'}
      </Typography.Text>
    </Flex>
  );
}
