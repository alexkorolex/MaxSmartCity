import { useState } from 'react';

import { useCreateReport } from '@/entities/report';
import type { Priority } from '@/entities/report';

export function useReportForm(onSubmitted: (reportId: string) => void) {
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [urgency, setUrgency] = useState<Priority>('NORMAL');
  const [problemContinues, setProblemContinues] = useState(true);
  const [validationError, setValidationError] = useState<string | null>(null);

  const createReport = useCreateReport();

  const submit = () => {
    if (text.trim().length < 10) {
      setValidationError('Опишите проблему подробнее — минимум 10 символов');
      return;
    }
    setValidationError(null);

    createReport.mutate(
      {
        source_type: 'MAX',
        text: text.trim(),
        category_id: categoryId,
        urgency,
        problem_continues: problemContinues,
      },
      { onSuccess: (report) => onSubmitted(report.id) },
    );
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
    validationError,
    submit,
    isSubmitting: createReport.isPending,
    submitError: createReport.error,
  };
}
