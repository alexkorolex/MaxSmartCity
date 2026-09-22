import { Button, CellHeader, CellList, CellSimple, Radio, Switch, Textarea, Typography } from '@maxhub/max-ui';
import { useNavigate } from 'react-router-dom';

import { PRIORITY_LABELS, useProblemCategories, type Priority } from '@/entities/report';
import { ROUTES } from '@/shared/routes';
import { AsyncState } from '@/shared/ui';

import { useReportForm } from '../model/useReportForm';

const URGENCY_OPTIONS: Priority[] = ['LOW', 'NORMAL', 'HIGH', 'CRITICAL'];

export function ReportForm() {
  const navigate = useNavigate();
  const categories = useProblemCategories();
  const form = useReportForm((reportId) => navigate(ROUTES.myReports, { state: { createdReportId: reportId } }));

  return (
    <>
      <CellList mode="island" header={<CellHeader>Описание проблемы</CellHeader>}>
        <div style={{ padding: '8px 16px 16px' }}>
          <Textarea
            mode="primary"
            placeholder="Что случилось? Укажите как можно больше деталей — это поможет быстрее найти решение."
            value={form.text}
            onChange={(event) => form.setText(event.target.value)}
            rows={4}
          />
        </div>
      </CellList>

      <CellList mode="island" header={<CellHeader>Категория (необязательно)</CellHeader>}>
        <AsyncState isLoading={categories.isLoading} error={categories.error}>
          {categories.data?.map((category) => (
            <CellSimple
              key={category.id}
              title={category.name}
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

      <CellList mode="island" header={<CellHeader>Срочность</CellHeader>}>
        {URGENCY_OPTIONS.map((option) => (
          <CellSimple
            key={option}
            title={PRIORITY_LABELS[option]}
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

      <CellList mode="island">
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

      {form.validationError && (
        <Typography.Text variant="description" color="secondary" style={{ color: 'var(--error)' }}>
          {form.validationError}
        </Typography.Text>
      )}
      {form.submitError && (
        <Typography.Text variant="description" style={{ color: 'var(--error)' }}>
          Не удалось отправить обращение. Попробуйте ещё раз.
        </Typography.Text>
      )}

      <Button variant="primary" size="large" stretched loading={form.isSubmitting} onClick={form.submit}>
        Отправить
      </Button>
    </>
  );
}
