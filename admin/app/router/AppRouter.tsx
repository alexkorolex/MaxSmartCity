import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';

import { AnalyticsPage } from '@/pages/analytics';
import { ConversationPage, CorrespondencePage } from '@/pages/correspondence';
import { HomePage } from '@/pages/home';
import { HousesPage } from '@/pages/houses';
import { MessagesPage } from '@/pages/messages';
import { IncidentDetailPage } from '@/pages/incident-detail';
import { IncidentsPage } from '@/pages/incidents';
import { NewsPage } from '@/pages/news';
import { OrganizationDetailPage } from '@/pages/organization-detail';
import { OrganizationsPage } from '@/pages/organizations';
import { ProfilePage } from '@/pages/profile';
import { ReportChatPage } from '@/pages/report-chat';
import { ReportDetailPage } from '@/pages/report-detail';
import { ResidentDetailPage } from '@/pages/resident-detail';
import { ResidentsPage } from '@/pages/residents';
import { StaffPage } from '@/pages/staff';
import { TerritoriesPage } from '@/pages/territories';
import { ROUTES } from '@/shared/routes';

import { AppLayout } from './AppLayout';
import { RequireStaffSession } from './RequireStaffSession';

const MapPage = lazy(() => import('@/pages/map').then((module) => ({ default: module.MapPage })));

export function AppRouter() {
  return (
    <Routes>
      <Route element={<RequireStaffSession />}>
        <Route element={<AppLayout />}>
          <Route path={ROUTES.home} element={<HomePage />} />
          <Route path={ROUTES.organizations} element={<OrganizationsPage />} />
          <Route path="/organizations/:organizationId" element={<OrganizationDetailPage />} />
          <Route path={ROUTES.houses} element={<HousesPage />} />
          <Route path={ROUTES.messages} element={<MessagesPage />} />
          <Route path={ROUTES.staff} element={<StaffPage />} />
          <Route path={ROUTES.residents} element={<ResidentsPage />} />
          <Route path="/residents/:residentId" element={<ResidentDetailPage />} />
          <Route path="/reports/:reportId" element={<ReportDetailPage />} />
          <Route path="/reports/:reportId/chat" element={<ReportChatPage />} />
          <Route path={ROUTES.incidents} element={<IncidentsPage />} />
          <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
          <Route path={ROUTES.news} element={<NewsPage />} />
          <Route path={ROUTES.profile} element={<ProfilePage />} />
          <Route path={ROUTES.territories} element={<TerritoriesPage />} />
          <Route path={ROUTES.analytics} element={<AnalyticsPage />} />
          <Route
            path={ROUTES.map}
            element={
              <Suspense fallback={null}>
                <MapPage />
              </Suspense>
            }
          />
          <Route path={ROUTES.correspondence} element={<CorrespondencePage />} />
          <Route path="/correspondence/:conversationId" element={<ConversationPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
