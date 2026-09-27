import { Button, CellHeader, CellList, CellSimple, Flex, Input, Typography } from '@maxhub/max-ui';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { useHouse } from '@/entities/geo';
import { UserAvatar, useMyProfile, useUpdateMyProfile } from '@/entities/user';
import { LogoutButton } from '@/features/logout';
import { ROUTES } from '@/shared/routes';
import { AsyncState, HelpIcon, HouseIcon, ListCard, PageLayout, SettingsIcon } from '@/shared/ui';

import './ProfilePage.css';

export function ProfilePage() {
  const profile = useMyProfile();
  const updateProfile = useUpdateMyProfile();
  const [displayName, setDisplayName] = useState('');

  useEffect(() => {
    if (profile.data) setDisplayName(profile.data.display_name ?? '');
  }, [profile.data]);

  const hasChanges = profile.data && displayName.trim() !== (profile.data.display_name ?? '');
  const myHouse = useHouse(profile.data?.house_id).data;

  return (
    <PageLayout title="Профиль">
      <AsyncState isLoading={profile.isLoading} error={profile.error} onRetry={() => profile.refetch()}>
        {profile.data && (
          <>
            <Flex
              align="center"
              className="surface-card profile-hero"
            >
              <UserAvatar name={displayName || profile.data.username || 'Резидент'} size={64} />
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

            <ListCard>
              <CellList mode="full-width" header={<CellHeader>Мой дом</CellHeader>}>
                <CellSimple
                  asChild
                  title={myHouse ? [myHouse.street, myHouse.house_number].filter(Boolean).join(', ') : 'Не указан'}
                  subtitle={myHouse ? myHouse.city ?? undefined : 'Укажите город и дом, чтобы видеть его проблемы'}
                  subtitleMode="tertiary"
                  before={<HouseIcon width={20} height={20} />}
                  showChevron
                >
                  <Link to={ROUTES.selectHouse} />
                </CellSimple>
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
