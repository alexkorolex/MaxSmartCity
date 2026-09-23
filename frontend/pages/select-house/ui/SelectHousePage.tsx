import { Button, Flex, Typography } from '@maxhub/max-ui';
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useMyProfile, useUpdateMyProfile } from '@/entities/user';
import { HouseSelector } from '@/features/select-house';
import { ROUTES } from '@/shared/routes';
import { AsyncState, PageLayout } from '@/shared/ui';

interface SelectHouseLocationState {
  mode?: 'onboarding';
}

export function SelectHousePage() {
  const profile = useMyProfile();
  const updateProfile = useUpdateMyProfile();
  const navigate = useNavigate();
  const location = useLocation();
  const isOnboarding = (location.state as SelectHouseLocationState | null)?.mode === 'onboarding';

  const [houseId, setHouseId] = useState<string | null>(null);

  useEffect(() => {
    if (profile.data) setHouseId(profile.data.house_id);
  }, [profile.data]);

  const handleSave = () => {
    if (!houseId) return;
    updateProfile.mutate(
      { house_id: houseId },
      { onSuccess: () => navigate(isOnboarding ? ROUTES.home : ROUTES.profile, { replace: true }) },
    );
  };

  return (
    <PageLayout
      title={isOnboarding ? 'Где вы живёте?' : 'Мой дом'}
      subtitle={
        isOnboarding
          ? 'Укажите город и дом — так мы сможем показывать проблемы именно вашего дома'
          : 'Вы можете изменить город и дом в любой момент'
      }
      backTo={isOnboarding ? undefined : ROUTES.profile}
    >
      <AsyncState isLoading={profile.isLoading} error={profile.error}>
        <Flex direction="column" gap="var(--space-4)">
          <HouseSelector value={houseId} onChange={setHouseId} />

          <Flex direction="column" gap="var(--space-2)">
            <Button
              variant="primary"
              size="large"
              stretched
              loading={updateProfile.isPending}
              disabled={!houseId}
              onClick={handleSave}
            >
              Сохранить
            </Button>
            {isOnboarding && (
              <Button variant="ghost" size="medium" stretched onClick={() => navigate(ROUTES.home)}>
                Пропустить, я укажу позже
              </Button>
            )}
          </Flex>

          {updateProfile.isError && (
            <Typography.Text variant="description" style={{ color: 'var(--error)' }}>
              Не удалось сохранить дом. Попробуйте ещё раз.
            </Typography.Text>
          )}
        </Flex>
      </AsyncState>
    </PageLayout>
  );
}
