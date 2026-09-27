import { Button, Flex, Spinner, Typography } from '@maxhub/max-ui';
import { useEffect } from 'react';
import { Outlet, useNavigate } from 'react-router-dom';

import { useMaxWebAppSignIn, useSession } from '@/entities/session';
import { consumeMaxStartRoute } from '@/shared/routes';
import { CityIcon, PageLayout } from '@/shared/ui';

import './RequireSession.css';

const MAX_BOT_URL = import.meta.env.VITE_MAX_BOT_URL;

function OpenBotPrompt() {
  return (
    <PageLayout withNavSpacing={false}>
      <Flex
        className="session-prompt"
        direction="column"
        align="center"
        justify="center"
      >
        <Flex className="surface-card session-prompt__card" direction="column" align="center" gap="var(--space-3)">
          <span className="session-prompt__brand"><CityIcon width={28} height={28} /></span>
          <Typography.Text asChild variant="title" color="primary"><h1>Smart City</h1></Typography.Text>
          <Typography.Text className="session-prompt__description" variant="description" color="secondary">
            {
            MAX_BOT_URL
              ? 'Откройте городского бота в MAX и нажмите «Начать», чтобы безопасно войти.'
              : 'Откройте бота в MAX и отправьте /start, чтобы войти.'
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

function SigningInPlaceholder() {
  return (
    <PageLayout withNavSpacing={false}>
      <Flex className="session-prompt" direction="column" align="center" justify="center" gap="var(--space-3)">
        <Spinner size={24} appearance="primary" />
        <Typography.Text variant="body" color="secondary">Выполняем вход…</Typography.Text>
      </Flex>
    </PageLayout>
  );
}

export function RequireSession() {
  const { isAuthenticated } = useSession();
  const signingIn = useMaxWebAppSignIn(!isAuthenticated);
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) return;
    const route = consumeMaxStartRoute();
    if (route) navigate(route);
  }, [isAuthenticated, navigate]);

  if (!isAuthenticated) return signingIn ? <SigningInPlaceholder /> : <OpenBotPrompt />;

  return <Outlet />;
}
