import { Route, Routes } from 'react-router-dom';

import { AuthMaxPage } from '@/pages/auth-max';
import { HelpPage } from '@/pages/help';
import { HomePage } from '@/pages/home';
import { IncidentCardPage } from '@/pages/incident-card';
import { IncidentResolutionPage } from '@/pages/incident-resolution';
import { MyHousePage } from '@/pages/my-house';
import { MyReportsPage } from '@/pages/my-reports';
import { NewsPage } from '@/pages/news';
import { NewsItemPage } from '@/pages/news-item';
import { NotificationsPage } from '@/pages/notifications';
import { ProfilePage } from '@/pages/profile';
import { ReportNewPage } from '@/pages/report-new';
import { SettingsPage } from '@/pages/settings';
import { ROUTES } from '@/shared/routes';

import { AppLayout } from './AppLayout';
import { RequireSession } from './RequireSession';

export function AppRouter() {
  return (
    <Routes>
      <Route path={ROUTES.authMax} element={<AuthMaxPage />} />

      <Route element={<RequireSession />}>
        <Route element={<AppLayout />}>
          <Route path={ROUTES.home} element={<HomePage />} />
          <Route path={ROUTES.reportNew} element={<ReportNewPage />} />
          <Route path={ROUTES.myReports} element={<MyReportsPage />} />
          <Route path="/incidents/:incidentId" element={<IncidentCardPage />} />
          <Route path="/incidents/:incidentId/resolution" element={<IncidentResolutionPage />} />
          <Route path={ROUTES.myHouse} element={<MyHousePage />} />
          <Route path={ROUTES.news} element={<NewsPage />} />
          <Route path="/news/:newsId" element={<NewsItemPage />} />
          <Route path={ROUTES.notifications} element={<NotificationsPage />} />
          <Route path={ROUTES.profile} element={<ProfilePage />} />
          <Route path={ROUTES.settings} element={<SettingsPage />} />
          <Route path={ROUTES.help} element={<HelpPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
