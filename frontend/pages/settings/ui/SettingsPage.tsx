import { CellHeader, CellList, CellSimple, Switch } from '@maxhub/max-ui';

import { ThemeSwitch } from '@/features/change-theme';
import { useMyProfile, useUpdateMyProfile } from '@/entities/user';
import { AsyncState, ListCard, PageLayout } from '@/shared/ui';
import { ROUTES } from '@/shared/routes';

export function SettingsPage() {
  const profile = useMyProfile();
  const updateProfile = useUpdateMyProfile();

  return (
    <PageLayout title="Настройки" subtitle="Внешний вид и уведомления" backTo={ROUTES.profile} withNavSpacing={false}>
      <ThemeSwitch />

      <AsyncState isLoading={profile.isLoading} error={profile.error}>
        {profile.data && (
          <ListCard>
          <CellList mode="full-width" header={<CellHeader>Уведомления</CellHeader>}>
            <CellSimple
              title="Push-уведомления в MAX"
              subtitle="Получать сообщения от бота об изменении статуса обращений"
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
