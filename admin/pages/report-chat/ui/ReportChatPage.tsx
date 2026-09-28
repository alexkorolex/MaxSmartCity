import { useParams } from 'react-router-dom';

import { ReportChatCard } from '@/features/report-chat';
import { ROUTES } from '@/shared/routes';

import './ReportChatPage.css';

export function ReportChatPage() {
  const { reportId = '' } = useParams();

  return (
    <div className="report-chat-page">
      <ReportChatCard reportId={reportId} backTo={ROUTES.report(reportId)} />
    </div>
  );
}
