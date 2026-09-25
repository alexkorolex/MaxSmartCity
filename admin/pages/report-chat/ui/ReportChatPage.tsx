import { Link, useParams } from 'react-router-dom';

import { ReportChatCard } from '@/features/report-chat';
import { ROUTES } from '@/shared/routes';
import { ArrowLeftIcon } from '@/shared/ui';

import './ReportChatPage.css';

/** The chat with the resident on its own page, sized to the viewport - see the CSS. */
export function ReportChatPage() {
  const { reportId = '' } = useParams();

  return (
    <div className="report-chat-page">
      <div className="page-back">
        <Link to={ROUTES.report(reportId)} className="btn btn--ghost btn--small">
          <ArrowLeftIcon width={16} height={16} />
          К обращению
        </Link>
      </div>
      <ReportChatCard reportId={reportId} />
    </div>
  );
}
