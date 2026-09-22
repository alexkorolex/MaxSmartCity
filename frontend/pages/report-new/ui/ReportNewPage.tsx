import { ReportForm } from '@/features/submit-report';
import { PageLayout } from '@/shared/ui';

export function ReportNewPage() {
  return (
    <PageLayout title="Сообщить о проблеме">
      <ReportForm />
    </PageLayout>
  );
}
