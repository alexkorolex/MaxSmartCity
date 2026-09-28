import { useParams } from 'react-router-dom';

import { useReport } from '@/entities/report';
import { ReportChat } from '@/features/report-chat';
import { ROUTES } from '@/shared/routes';

import './ReportChatPage.css';

export function ReportChatPage() {
  const { reportId = '' } = useParams<{ reportId: string }>();
  const report = useReport(reportId);

  return (
    <main className="report-chat-page">
      <ReportChat
        reportId={reportId}
        reportText={report.data?.text ?? undefined}
        backTo={ROUTES.report(reportId)}
      />
    </main>
  );
}
