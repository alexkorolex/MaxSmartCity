import { Flex, Typography } from '@maxhub/max-ui';
import { Outlet } from 'react-router-dom';

import { useSession } from '@/entities/session';
import { EmptyState, PageLayout } from '@/shared/ui';

const MAX_BOT_URL = import.meta.env.VITE_MAX_BOT_URL;

function OpenBotPrompt() {
  return (
    <PageLayout title="Max Smart City" withNavSpacing={false}>
      <Flex direction="column" align="center" gap={16} style={{ paddingTop: 48 }}>
        <EmptyState
          title="Вход через MAX"
          description={
            MAX_BOT_URL
              ? 'Откройте бота Max Smart City в MAX и нажмите «Начать», чтобы войти в приложение.'
              : 'Откройте бота Max Smart City в мессенджере MAX и нажмите /start или /login, чтобы получить ссылку для входа.'
          }
        />
        {MAX_BOT_URL && (
          <Typography.Text asChild variant="action-medium">
            <a href={MAX_BOT_URL} style={{ color: 'var(--blue)' }}>
              Открыть бота в MAX
            </a>
          </Typography.Text>
        )}
      </Flex>
    </PageLayout>
  );
}

export function RequireSession() {
  const { isAuthenticated } = useSession();

  if (!isAuthenticated) return <OpenBotPrompt />;

  return <Outlet />;
}
