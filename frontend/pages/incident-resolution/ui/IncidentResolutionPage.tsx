import { Button, Flex, Textarea, Typography } from '@maxhub/max-ui';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import {
  canConfirmOrDispute,
  useConfirmResolution,
  useDisputeResolution,
  useIncident,
} from '@/entities/incident';
import { ROUTES } from '@/shared/routes';
import { AsyncState, CheckCircleIcon, EmptyState, PageLayout } from '@/shared/ui';

import './IncidentResolutionPage.css';

export function IncidentResolutionPage() {
  const { incidentId = '' } = useParams<{ incidentId: string }>();
  const navigate = useNavigate();
  const incident = useIncident(incidentId);
  const confirmResolution = useConfirmResolution(incidentId);
  const disputeResolution = useDisputeResolution(incidentId);
  const [comment, setComment] = useState('');
  const [isDisputing, setIsDisputing] = useState(false);

  const handleConfirm = () => {
    confirmResolution.mutate(undefined, {
      onSuccess: () => navigate(ROUTES.incident(incidentId), { replace: true }),
    });
  };

  const handleDispute = () => {
    if (comment.trim().length < 5) return;
    disputeResolution.mutate(comment.trim(), {
      onSuccess: () => navigate(ROUTES.incident(incidentId), { replace: true }),
    });
  };

  return (
    <PageLayout title="Проверка решения" subtitle="Подтвердите результат работ" backTo={ROUTES.incident(incidentId)} withNavSpacing={false}>
      <AsyncState isLoading={incident.isLoading} error={incident.error}>
        {incident.data && !canConfirmOrDispute(incident.data.status) && (
          <EmptyState
            icon={<CheckCircleIcon width={28} height={28} />}
            title="Сейчас нечего подтверждать"
            description="Этот инцидент не ожидает подтверждения решения."
          />
        )}

        {incident.data && canConfirmOrDispute(incident.data.status) && (
          <>
            <Flex
              direction="column"
              align="center"
              gap="var(--space-3)"
              className="surface-card incident-resolution-summary"
            >
              <Flex className="incident-resolution-summary__icon" align="center" justify="center">
                <CheckCircleIcon width={26} height={26} />
              </Flex>
              <Typography.Text variant="body-strong" color="primary">
                «{incident.data.title}»
              </Typography.Text>
              <Typography.Text variant="description" color="secondary">
                Отмечена как решённая. Подтвердите, если проблема действительно устранена, или сообщите, что она
                осталась.
              </Typography.Text>
            </Flex>

            {!isDisputing ? (
              <Flex direction="column" gap="var(--space-2)">
                <Button
                  variant="primary"
                  size="large"
                  stretched
                  loading={confirmResolution.isPending}
                  onClick={handleConfirm}
                >
                  Да, проблема решена
                </Button>
                <Button variant="destructive" size="large" stretched onClick={() => setIsDisputing(true)}>
                  Проблема не решена
                </Button>
              </Flex>
            ) : (
              <Flex direction="column" gap="var(--space-2)">
                <Textarea
                  mode="primary"
                  placeholder="Опишите, что именно не решено"
                  value={comment}
                  onChange={(event) => setComment(event.target.value)}
                  rows={4}
                />
                <Button
                  variant="destructive"
                  size="large"
                  stretched
                  loading={disputeResolution.isPending}
                  disabled={comment.trim().length < 5}
                  onClick={handleDispute}
                >
                  Оспорить решение
                </Button>
                <Button variant="ghost" size="medium" stretched onClick={() => setIsDisputing(false)}>
                  Отмена
                </Button>
              </Flex>
            )}
          </>
        )}
      </AsyncState>
    </PageLayout>
  );
}
