import { Route, Routes } from 'react-router-dom';

import { HomePage } from '@/pages/home';
import { IncidentDetailPage } from '@/pages/incident-detail';
import { IncidentsPage } from '@/pages/incidents';
import { NewsPage } from '@/pages/news';
import { OrganizationsPage } from '@/pages/organizations';
import { ReportDetailPage } from '@/pages/report-detail';
import { ResidentDetailPage } from '@/pages/resident-detail';
import { ResidentsPage } from '@/pages/residents';
import { StaffPage } from '@/pages/staff';
import { ROUTES } from '@/shared/routes';

import { AppLayout } from './AppLayout';
import { RequireStaffSession } from './RequireStaffSession';

export function AppRouter() {
  return (
    <Routes>
      <Route element={<RequireStaffSession />}>
        <Route element={<AppLayout />}>
          <Route path={ROUTES.home} element={<HomePage />} />
          <Route path={ROUTES.organizations} element={<OrganizationsPage />} />
          <Route path={ROUTES.staff} element={<StaffPage />} />
          <Route path={ROUTES.residents} element={<ResidentsPage />} />
          <Route path="/residents/:residentId" element={<ResidentDetailPage />} />
          <Route path="/reports/:reportId" element={<ReportDetailPage />} />
          <Route path={ROUTES.incidents} element={<IncidentsPage />} />
          <Route path="/incidents/:incidentId" element={<IncidentDetailPage />} />
          <Route path={ROUTES.news} element={<NewsPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
