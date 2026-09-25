import { Button, Flex, Textarea, Typography } from '@maxhub/max-ui';
import { useState } from 'react';

import { FINAL_REPORT_STATUSES, useCloseReport, type Report } from '@/entities/report';

/**
 * "Проблема решилась": the resident closes their own report. Two steps - a tap first
 * reveals the (optional) comment and the confirmation, so it can't happen by accident.
 */
export function CloseReportCard({ report }: { report: Report }) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [comment, setComment] = useState('');
  const closeReport = useCloseReport(report.id);

  if (FINAL_REPORT_STATUSES.has(report.status)) return null;

  return (
    <Flex direction="column" gap="var(--space-3)" className="surface-card close-report">
      <Typography.Text variant="body-strong" color="primary">
        Проблема уже решилась?
      </Typography.Text>
      <Typography.Text variant="description" color="secondary">
        Закройте обращение, чтобы службы не тратили на него время. Если о проблеме сообщали и соседи, их
        обращения останутся в работе.
      </Typography.Text>

      {isConfirming ? (
        <>
          <Textarea
            mode="primary"
            placeholder="Что изменилось? Необязательно"
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            rows={3}
          />
          {closeReport.isError && (
            <Typography.Text variant="description" className="close-report__error">
              Не удалось закрыть обращение. Проверьте соединение и попробуйте ещё раз.
            </Typography.Text>
          )}
          <Button
            variant="primary"
            size="large"
            stretched
            loading={closeReport.isPending}
            onClick={() => closeReport.mutate(comment.trim() || null)}
          >
            Закрыть обращение
          </Button>
          <Button variant="ghost" size="medium" stretched onClick={() => setIsConfirming(false)}>
            Отмена
          </Button>
        </>
      ) : (
        <Button variant="secondary" size="large" stretched onClick={() => setIsConfirming(true)}>
          Да, проблема решилась
        </Button>
      )}
    </Flex>
  );
}
