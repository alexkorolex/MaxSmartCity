import { useEffect, useRef, useState } from 'react';

import { useCreateReport, uploadReportAttachment } from '@/entities/report';
import type { Priority } from '@/entities/report';
import { useMyProfile } from '@/entities/user';

import { usePhotoPicker } from './usePhotoPicker';

export function useReportForm(onSubmitted: (reportId: string) => void) {
  const profile = useMyProfile();
  const [categoryCode, setCategoryCode] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [urgency, setUrgency] = useState<Priority>('NORMAL');
  const [problemContinues, setProblemContinues] = useState(true);
  const [houseId, setHouseId] = useState<string | null>(null);
  const [isEditingHouse, setIsEditingHouse] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [attachmentWarning, setAttachmentWarning] = useState<string | null>(null);
  const request = useRef<{ signature: string; id: string } | null>(null);

  useEffect(() => {
    if (profile.data) setHouseId((current) => current ?? profile.data.house_id);
  }, [profile.data]);

  const photoPicker = usePhotoPicker();
  const createReport = useCreateReport();
  const [createdReportId, setCreatedReportId] = useState<string | null>(null);

  const submit = () => {
    if (text.trim().length < 10) {
      setValidationError('Опишите проблему подробнее — минимум 10 символов');
      return;
    }
    if (!categoryCode) {
      setValidationError('Выберите тип обращения');
      return;
    }
    if (!houseId) {
      setValidationError('Выберите дом');
      return;
    }
    setValidationError(null);
    setAttachmentWarning(null);

    const signature = JSON.stringify([houseId, categoryCode, text.trim(), urgency, problemContinues]);
    if (request.current?.signature !== signature) {
      request.current = { signature, id: crypto.randomUUID() };
    }
    const requestId = request.current.id;

    createReport.mutate(
      {
        source_external_id: requestId,
        request_id: requestId,
        house_id: houseId,
        category_code: categoryCode,
        text: text.trim(),
        urgency,
        problem_continues: problemContinues,
      },
      {
        onSuccess: async (result) => {
          if (photoPicker.photos.length === 0) {
            onSubmitted(result.report_id);
            return;
          }
          const results = await Promise.allSettled(
            photoPicker.photos.map((photo) => uploadReportAttachment(result.report_id, photo.file)),
          );
          const failedCount = results.filter((result) => result.status === 'rejected').length;
          if (failedCount === 0) {
            onSubmitted(result.report_id);
            return;
          }
          setCreatedReportId(result.report_id);
          setAttachmentWarning(
            failedCount === photoPicker.photos.length
              ? 'Обращение отправлено, но фото загрузить не удалось.'
              : `Обращение отправлено, но ${failedCount} из ${photoPicker.photos.length} фото не загрузилось.`,
          );
        },
      },
    );
  };

  const dismissAttachmentWarning = () => {
    if (createdReportId) onSubmitted(createdReportId);
  };

  return {
    categoryCode,
    setCategoryCode,
    text,
    setText,
    urgency,
    setUrgency,
    problemContinues,
    setProblemContinues,
    houseId,
    setHouseId,
    isEditingHouse,
    setIsEditingHouse,
    photoPicker,
    validationError,
    attachmentWarning,
    dismissAttachmentWarning,
    submit,
    isSubmitting: createReport.isPending,
    submitError: createReport.error,
  };
}
