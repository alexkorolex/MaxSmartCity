import { Avatar, Button, CellHeader, CellList, CellSimple, Flex, Input, Typography } from '@maxhub/max-ui';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { useMyProfile, useUpdateMyProfile } from '@/entities/user';
import { LogoutButton } from '@/features/logout';
import { ROUTES } from '@/shared/routes';
import { AsyncState, HelpIcon, ListCard, PageLayout, SettingsIcon } from '@/shared/ui';

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
            <Flex
              align="center"
              className="surface-card profile-hero"
            >
              <Avatar.Container size={64}>
                <Avatar.Image
                  alt={displayName || 'Резидент'}
                  fallback={initialsOf(profile.data.display_name)}
                  fallbackGradient="blue"
                />
              </Avatar.Container>
              <Flex className="profile-hero__copy" direction="column" gap="var(--space-1)">
                <Typography.Text className="profile-hero__name" variant="title" color="primary">
                  {profile.data.display_name || 'Житель города'}
                </Typography.Text>
                <Typography.Text variant="description" color="secondary">
                  {profile.data.username ? `@${profile.data.username}` : 'Профиль жителя'}
                </Typography.Text>
              </Flex>
            </Flex>

            <ListCard>
              <CellList mode="full-width" header={<CellHeader>Имя в приложении</CellHeader>}>
                <div className="field-card__body">
                  <Input
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    placeholder="Ваше имя"
                    hint="Видно только вам в интерфейсе приложения"
                  />
                </div>
              </CellList>
            </ListCard>

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

            <ListCard>
              <CellList mode="full-width">
                <CellSimple asChild title="Настройки" before={<SettingsIcon width={20} height={20} />} showChevron separator>
                  <Link to={ROUTES.settings} />
                </CellSimple>
                <CellSimple asChild title="Помощь и обратная связь" before={<HelpIcon width={20} height={20} />} showChevron>
                  <Link to={ROUTES.help} />
                </CellSimple>
              </CellList>
            </ListCard>

            <ListCard><CellList mode="full-width"><LogoutButton /></CellList></ListCard>
          </>
        )}
      </AsyncState>
    </PageLayout>
  );
}
