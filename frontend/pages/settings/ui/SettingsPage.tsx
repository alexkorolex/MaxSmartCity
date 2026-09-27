import { CellHeader, CellList, CellSimple, Switch } from '@maxhub/max-ui';

import { ThemeSwitch } from '@/features/change-theme';
import { useMyProfile, useUpdateMyProfile, type ResidentProfile } from '@/entities/user';
import { AsyncState, ListCard, PageLayout } from '@/shared/ui';
import { ROUTES } from '@/shared/routes';

function maxNotificationsHint(profile: ResidentProfile): string {
  if (profile.bot_status === 'STOPPED') {
    return 'Бот остановлен — откройте чат с ботом в MAX и нажмите «Старт», чтобы снова получать сообщения';
  }
  if (!profile.max_chat_id) {
    return 'Чтобы сообщения приходили, откройте чат с ботом в MAX и отправьте /start';
  }
  return 'Бот пришлёт в MAX изменения статуса обращений и новые сообщения от управляющей компании';
}

export function SettingsPage() {
  const profile = useMyProfile();
  const updateProfile = useUpdateMyProfile();

  return (
    <PageLayout title="Настройки" subtitle="Внешний вид и уведомления" backTo={ROUTES.profile} backLabel="Профиль" withNavSpacing={false}>
      <ThemeSwitch />

      <AsyncState isLoading={profile.isLoading} error={profile.error}>
        {profile.data && (
          <ListCard>
          <CellList mode="full-width" header={<CellHeader>Уведомления</CellHeader>}>
            <CellSimple
              title="Push-уведомления в MAX"
              subtitle={maxNotificationsHint(profile.data)}
              subtitleMode="tertiary"
              after={
                <Switch
                  checked={profile.data.notifications_enabled}
                  disabled={updateProfile.isPending}
                  onChange={(event) => updateProfile.mutate({ notifications_enabled: event.target.checked })}
                  aria-label="Push-уведомления"
                />
              }
            />
          </CellList>
          </ListCard>
        )}
      </AsyncState>
    </PageLayout>
  );
}
