import { CellHeader, CellList, CellSimple, Switch } from '@maxhub/max-ui';

import { ThemeSwitch } from '@/features/change-theme';
import { useMyProfile, useUpdateMyProfile } from '@/entities/user';
import { AsyncState, PageLayout } from '@/shared/ui';

export function SettingsPage() {
  const profile = useMyProfile();
  const updateProfile = useUpdateMyProfile();

  return (
    <PageLayout title="Настройки">
      <ThemeSwitch />

      <AsyncState isLoading={profile.isLoading} error={profile.error}>
        {profile.data && (
          <CellList mode="island" header={<CellHeader>Уведомления</CellHeader>}>
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
        )}
      </AsyncState>
    </PageLayout>
  );
}
