import { Button, Flex, Typography } from '@maxhub/max-ui';
import { Outlet } from 'react-router-dom';

import { useSession } from '@/entities/session';
import { CityIcon, PageLayout } from '@/shared/ui';

const MAX_BOT_URL = import.meta.env.VITE_MAX_BOT_URL;

function OpenBotPrompt() {
  return (
    <PageLayout withNavSpacing={false}>
      <Flex
        className="auth-stage"
        direction="column"
        align="center"
        justify="center"
      >
        <Flex className="surface-card auth-card" direction="column" align="center" gap="var(--space-3)">
          <span className="brand-mark"><CityIcon width={28} height={28} /></span>
          <Typography.Text asChild variant="title" color="primary"><h1>Smart City</h1></Typography.Text>
          <Typography.Text variant="description" color="secondary" style={{ maxWidth: 320 }}>
            {
            MAX_BOT_URL
              ? 'Откройте городского бота в MAX и нажмите «Начать», чтобы безопасно войти.'
              : 'Откройте бота в MAX и отправьте /start или /login, чтобы получить ссылку для входа.'
            }
          </Typography.Text>
          {MAX_BOT_URL && (
            <Button asChild variant="primary" size="large" stretched>
              <a href={MAX_BOT_URL}>Открыть бота в MAX</a>
            </Button>
          )}
        </Flex>
      </Flex>
    </PageLayout>
  );
}

export function RequireSession() {
  const { isAuthenticated } = useSession();

  if (!isAuthenticated) return <OpenBotPrompt />;

  return <Outlet />;
}
