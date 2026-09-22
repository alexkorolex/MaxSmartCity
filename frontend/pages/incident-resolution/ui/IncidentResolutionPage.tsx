import { Button, Textarea, Typography } from '@maxhub/max-ui';
import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';

import {
  canConfirmOrDispute,
  useConfirmResolution,
  useDisputeResolution,
  useIncident,
} from '@/entities/incident';
import { ROUTES } from '@/shared/routes';
import { AsyncState, EmptyState, PageLayout } from '@/shared/ui';

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
    <PageLayout title="Решение по проблеме">
      <AsyncState isLoading={incident.isLoading} error={incident.error}>
        {incident.data && !canConfirmOrDispute(incident.data.status) && (
          <EmptyState
            title="Сейчас нечего подтверждать"
            description="Этот инцидент не ожидает подтверждения решения."
          />
        )}

        {incident.data && canConfirmOrDispute(incident.data.status) && (
          <>
            <Typography.Text variant="body" color="primary">
              «{incident.data.title}» отмечена как решённая. Подтвердите, если проблема действительно устранена,
              или сообщите, что она осталась.
            </Typography.Text>

            {!isDisputing ? (
              <>
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
              </>
            ) : (
              <>
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
              </>
            )}
          </>
        )}
      </AsyncState>
    </PageLayout>
  );
}
