import { ReportForm } from '@/features/submit-report';
import { PageLayout } from '@/shared/ui';
import { ROUTES } from '@/shared/routes';

export function ReportNewPage() {
  return (
    <PageLayout title="Новое обращение" subtitle="Опишите ситуацию — это займёт пару минут" backTo={ROUTES.home} withNavSpacing={false}>
      <ReportForm />
    </PageLayout>
  );
}
