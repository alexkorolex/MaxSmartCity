import { Button, CellHeader, CellList, CellSimple, Flex, Radio, Switch, Textarea, Typography } from '@maxhub/max-ui';
import { useNavigate } from 'react-router-dom';

import { PRIORITY_LABELS, PRIORITY_TONES, useProblemCategories, type Priority } from '@/entities/report';
import { ROUTES } from '@/shared/routes';
import { AsyncState, ListCard, ToneDot, WarningIcon } from '@/shared/ui';

import { useReportForm } from '../model/useReportForm';

const URGENCY_OPTIONS: Priority[] = ['LOW', 'NORMAL', 'HIGH', 'CRITICAL'];

export function ReportForm() {
  const navigate = useNavigate();
  const categories = useProblemCategories();
  const form = useReportForm((reportId) => navigate(ROUTES.myReports, { state: { createdReportId: reportId } }));

  return (
    <div className="form-stack">
      <ListCard>
      <CellList mode="full-width" header={<CellHeader>Описание проблемы</CellHeader>}>
        <div className="field-card__body">
          <Textarea
            mode="primary"
            placeholder="Что случилось? Укажите как можно больше деталей — это поможет быстрее найти решение."
            value={form.text}
            onChange={(event) => form.setText(event.target.value)}
            rows={4}
          />
        </div>
      </CellList>
      </ListCard>

      <ListCard>
      <CellList mode="full-width" header={<CellHeader>Категория (необязательно)</CellHeader>}>
        <AsyncState isLoading={categories.isLoading} error={categories.error}>
          {categories.data?.map((category) => (
            <CellSimple
              key={category.id}
              title={category.name}
              before={category.is_critical ? <WarningIcon width={18} height={18} style={{ color: 'var(--error)' }} /> : undefined}
              after={
                <Radio
                  name="category"
                  checked={form.categoryId === category.id}
                  onChange={() => form.setCategoryId(category.id)}
                  aria-label={category.name}
                />
              }
            />
          ))}
        </AsyncState>
      </CellList>
      </ListCard>

      <ListCard>
      <CellList mode="full-width" header={<CellHeader>Срочность</CellHeader>}>
        {URGENCY_OPTIONS.map((option) => (
          <CellSimple
            key={option}
            title={PRIORITY_LABELS[option]}
            before={<ToneDot tone={PRIORITY_TONES[option]} />}
            after={
              <Radio
                name="urgency"
                checked={form.urgency === option}
                onChange={() => form.setUrgency(option)}
                aria-label={PRIORITY_LABELS[option]}
              />
            }
          />
        ))}
      </CellList>
      </ListCard>

      <ListCard>
      <CellList mode="full-width">
        <CellSimple
          title="Проблема ещё продолжается"
          subtitle="Отключите, если проблема уже устранена сама собой"
          subtitleMode="tertiary"
          after={
            <Switch
              checked={form.problemContinues}
              onChange={(event) => form.setProblemContinues(event.target.checked)}
              aria-label="Проблема ещё продолжается"
            />
          }
        />
      </CellList>
      </ListCard>

      {(form.validationError || form.submitError) && (
        <Flex
          className="surface-card"
          style={{ padding: 'var(--space-3) var(--space-4)', borderColor: 'var(--error)' }}
        >
          <Typography.Text variant="description" style={{ color: 'var(--error)' }}>
            {form.validationError ?? 'Не удалось отправить обращение. Попробуйте ещё раз.'}
          </Typography.Text>
        </Flex>
      )}

      <div className="sticky-submit">
        <Button variant="primary" size="large" stretched loading={form.isSubmitting} onClick={form.submit}>
          Отправить обращение
        </Button>
      </div>
    </div>
  );
}
