import { Button, CellHeader, CellList, CellSimple, Flex, Radio, Switch, Textarea, Typography } from '@maxhub/max-ui';
import { useNavigate } from 'react-router-dom';

import { HouseSelector } from '@/features/select-house';
import { useHouse } from '@/entities/geo';
import { PRIORITY_LABELS, PRIORITY_TONES, useProblemCategories, type Priority } from '@/entities/report';
import { ROUTES } from '@/shared/routes';
import { AsyncState, HouseIcon, ListCard, ToneDot, WarningIcon } from '@/shared/ui';

import { useReportForm } from '../model/useReportForm';
import { PhotoPicker } from './PhotoPicker';

import './ReportForm.css';

const URGENCY_OPTIONS: Priority[] = ['LOW', 'NORMAL', 'HIGH', 'CRITICAL'];

export function ReportForm() {
  const navigate = useNavigate();
  const categories = useProblemCategories();
  const form = useReportForm((reportId) => navigate(ROUTES.report(reportId), { replace: true }));

  const selectedHouse = useHouse(form.houseId).data;
  const criticalCategory = categories.data?.some(
    (category) => category.code === form.categoryCode && category.is_critical,
  );

  if (form.attachmentWarning) {
    return (
      <Flex className="report-form__success" direction="column" gap="var(--space-4)" align="center">
        <Typography.Text variant="body-strong" color="primary">
          Обращение отправлено
        </Typography.Text>
        <Typography.Text variant="description" color="secondary">
          {form.attachmentWarning}
        </Typography.Text>
        <Button variant="primary" size="large" stretched onClick={form.dismissAttachmentWarning}>
          Понятно, к обращению
        </Button>
      </Flex>
    );
  }

  return (
    <div className="form-stack">
      <ListCard>
        <CellList mode="full-width" header={<CellHeader>Тип обращения</CellHeader>}>
          <AsyncState isLoading={categories.isLoading} error={categories.error}>
            {categories.data?.map((category) => (
              <CellSimple
                key={category.id}
                title={category.name}
                before={
                  category.is_critical ? (
                    <WarningIcon className="report-form__critical-icon" width={18} height={18} />
                  ) : undefined
                }
                after={
                  <Radio
                    name="category"
                    checked={form.categoryCode === category.code}
                    onChange={() => {
                      form.setCategoryCode(category.code);
                      if (category.is_critical) form.setUrgency('CRITICAL');
                    }}
                    aria-label={category.name}
                  />
                }
              />
            ))}
          </AsyncState>
        </CellList>
      </ListCard>

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
        <CellList mode="full-width" header={<CellHeader>Фото (необязательно)</CellHeader>}>
          <div className="field-card__body">
            <PhotoPicker
              photos={form.photoPicker.photos}
              canAddMore={form.photoPicker.canAddMore}
              error={form.photoPicker.error}
              onAdd={form.photoPicker.addFiles}
              onRemove={form.photoPicker.removePhoto}
            />
          </div>
        </CellList>
      </ListCard>

      {form.isEditingHouse ? (
        <>
          <HouseSelector
            value={form.houseId}
            onChange={(houseId) => {
              form.setHouseId(houseId);
              form.setIsEditingHouse(false);
            }}
          />
          <Button variant="ghost" size="medium" stretched onClick={() => form.setIsEditingHouse(false)}>
            Отмена
          </Button>
        </>
      ) : (
        <ListCard>
          <CellList mode="full-width" header={<CellHeader>Адрес</CellHeader>}>
            <CellSimple
              title={
                selectedHouse
                  ? [selectedHouse.street, selectedHouse.house_number].filter(Boolean).join(', ')
                  : 'Адрес не указан'
              }
              subtitle={selectedHouse ? selectedHouse.formatted : 'Укажите, где произошла проблема'}
              subtitleMode="tertiary"
              before={<HouseIcon width={20} height={20} />}
              showChevron
              onClick={() => form.setIsEditingHouse(true)}
            />
          </CellList>
        </ListCard>
      )}

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
                  disabled={criticalCategory}
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
        <Flex className="form-feedback" role="alert">
          <Typography.Text variant="description" color="inherit">
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
