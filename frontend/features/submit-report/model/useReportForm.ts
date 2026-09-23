import { useEffect, useState } from 'react';

import { useCreateReport, uploadReportAttachment } from '@/entities/report';
import type { Priority } from '@/entities/report';
import { useMyProfile } from '@/entities/user';

import { usePhotoPicker } from './usePhotoPicker';

export function useReportForm(onSubmitted: (reportId: string) => void) {
  const profile = useMyProfile();
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [urgency, setUrgency] = useState<Priority>('NORMAL');
  const [problemContinues, setProblemContinues] = useState(true);
  const [houseId, setHouseId] = useState<string | null>(null);
  const [isEditingHouse, setIsEditingHouse] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [attachmentWarning, setAttachmentWarning] = useState<string | null>(null);

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
    setValidationError(null);
    setAttachmentWarning(null);

    createReport.mutate(
      {
        source_type: 'MAX',
        text: text.trim(),
        category_id: categoryId,
        urgency,
        problem_continues: problemContinues,
        house_id: houseId,
      },
      {
        onSuccess: async (report) => {
          if (photoPicker.photos.length === 0) {
            onSubmitted(report.id);
            return;
          }
          const results = await Promise.allSettled(
            photoPicker.photos.map((photo) => uploadReportAttachment(report.id, photo.file)),
          );
          const failedCount = results.filter((result) => result.status === 'rejected').length;
          if (failedCount === 0) {
            onSubmitted(report.id);
            return;
          }
          // The report itself is already safely created - only some photos failed to
          // attach. Stay on the page so the warning is actually seen before moving on.
          setCreatedReportId(report.id);
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
    categoryId,
    setCategoryId,
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
