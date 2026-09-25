import { useParams } from 'react-router-dom';

import { ReportChatCard } from '@/features/report-chat';
import { ROUTES } from '@/shared/routes';

import './ReportChatPage.css';

/** The chat with the resident on its own page, sized to the viewport - see the CSS. */
export function ReportChatPage() {
  const { reportId = '' } = useParams();

  return (
    <div className="report-chat-page">
      <ReportChatCard reportId={reportId} backTo={ROUTES.report(reportId)} />
    </div>
  );
}
