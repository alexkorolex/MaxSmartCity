import { Avatar, Button, CellHeader, CellList, CellSimple, Flex, Input } from '@maxhub/max-ui';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { LogoutButton } from '@/features/logout';
import { useMyProfile, useUpdateMyProfile } from '@/entities/user';
import { ROUTES } from '@/shared/routes';
import { AsyncState, PageLayout } from '@/shared/ui';

function initialsOf(name: string | null): string {
  if (!name) return '?';
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

export function ProfilePage() {
  const profile = useMyProfile();
  const updateProfile = useUpdateMyProfile();
  const [displayName, setDisplayName] = useState('');

  useEffect(() => {
    if (profile.data) setDisplayName(profile.data.display_name ?? '');
  }, [profile.data]);

  const hasChanges = profile.data && displayName.trim() !== (profile.data.display_name ?? '');

  return (
    <PageLayout title="Профиль">
      <AsyncState isLoading={profile.isLoading} error={profile.error} onRetry={() => profile.refetch()}>
        {profile.data && (
          <>
            <Flex direction="column" align="center" gap={8}>
              <Avatar.Container size={72}>
                <Avatar.Image alt={displayName || 'Резидент'} fallback={initialsOf(profile.data.display_name)} fallbackGradient="blue" />
              </Avatar.Container>
            </Flex>

            <CellList mode="island" header={<CellHeader>Данные профиля</CellHeader>}>
              <div style={{ padding: '8px 16px' }}>
                <Input
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  placeholder="Ваше имя"
                  hint="Отображается в приложении"
                />
              </div>
              {profile.data.username && <CellSimple title="Имя пользователя в MAX" subtitle={`@${profile.data.username}`} subtitleMode="tertiary" />}
            </CellList>

            {hasChanges && (
              <Button
                variant="primary"
                size="large"
                stretched
                loading={updateProfile.isPending}
                onClick={() => updateProfile.mutate({ display_name: displayName.trim() })}
              >
                Сохранить
              </Button>
            )}

            <CellList mode="island">
              <CellSimple asChild title="Настройки" showChevron>
                <Link to={ROUTES.settings} />
              </CellSimple>
              <CellSimple asChild title="Помощь и обратная связь" showChevron separator>
                <Link to={ROUTES.help} />
              </CellSimple>
            </CellList>

            <CellList mode="island">
              <LogoutButton />
            </CellList>
          </>
        )}
      </AsyncState>
    </PageLayout>
  );
}
