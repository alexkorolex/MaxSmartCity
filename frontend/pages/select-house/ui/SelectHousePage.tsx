import { Button, Flex, Typography } from '@maxhub/max-ui';
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { newsListQueryKey } from '@/entities/news';
import { useMyProfile, useUpdateMyProfile } from '@/entities/user';
import { HouseSelector } from '@/features/select-house';
import { ROUTES } from '@/shared/routes';
import { AsyncState, PageLayout } from '@/shared/ui';
import { HouseInfoSection } from '@/widgets/house-info';

import './SelectHousePage.css';

interface SelectHouseLocationState {
  mode?: 'onboarding';
}

export function SelectHousePage() {
  const profile = useMyProfile();
  const updateProfile = useUpdateMyProfile();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const location = useLocation();
  const isOnboarding = (location.state as SelectHouseLocationState | null)?.mode === 'onboarding';
  const [houseId, setHouseId] = useState<string | null>(null);
  const initialHouseId = profile.data?.house_id ?? null;
  const hasChanges = houseId !== initialHouseId;

  useEffect(() => {
    if (profile.data) setHouseId(profile.data.house_id);
  }, [profile.data]);

  const handleSave = () => {
    if (!houseId) return;
    updateProfile.mutate(
      { house_id: houseId },
      {
        onSuccess: () => {
          void queryClient.invalidateQueries({ queryKey: newsListQueryKey });
          navigate(isOnboarding ? ROUTES.home : ROUTES.profile, { replace: true });
        },
      },
    );
  };

  return (
    <PageLayout
      title={isOnboarding ? 'Где вы живёте?' : 'Мой дом'}
      eyebrow={isOnboarding ? 'Настройка профиля' : 'Ваш адрес'}
      subtitle={
        isOnboarding
          ? 'Найдите свой адрес, чтобы видеть события и проблемы рядом'
          : 'Найдите новый адрес — текущий изменится только после сохранения'
      }
      backTo={isOnboarding ? undefined : ROUTES.profile}
      backLabel="Профиль"
      withNavSpacing={false}
    >
      <AsyncState isLoading={profile.isLoading} error={profile.error}>
        <Flex direction="column" gap="var(--space-4)" className="house-selection-page">
          <HouseSelector value={houseId} onChange={setHouseId} />

          {houseId && <HouseInfoSection houseId={houseId} />}

          <Flex direction="column" gap="var(--space-2)" className="house-selection-actions">
            <Button
              variant="primary"
              size="large"
              stretched
              loading={updateProfile.isPending}
              disabled={!houseId || (!isOnboarding && !hasChanges)}
              onClick={handleSave}
            >
              {isOnboarding ? 'Продолжить' : 'Сохранить адрес'}
            </Button>
            {isOnboarding && (
              <Button variant="ghost" size="medium" stretched onClick={() => navigate(ROUTES.home)}>
                Пропустить, я укажу позже
              </Button>
            )}
          </Flex>

          {updateProfile.isError && (
            <div className="house-selection-error" role="alert">
              <Typography.Text variant="description" color="inherit">
                Не удалось сохранить адрес. Проверьте соединение и попробуйте ещё раз.
              </Typography.Text>
            </div>
          )}
        </Flex>
      </AsyncState>
    </PageLayout>
  );
}
