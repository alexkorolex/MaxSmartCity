import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { useTerritorySummary } from '@/entities/analytics';
import { useHouseManagement } from '@/entities/geo';
import { useIncidents } from '@/entities/incident';
import { useOrganization, useOrganizations } from '@/entities/organization';
import { useResidents } from '@/entities/resident';
import { canBrowseOrganizations, isAdmin, isAuthority, primaryRole, roleLabel, useMe, useProfile } from '@/entities/session';
import { useStaffList } from '@/entities/staff';
import { ROUTES } from '@/shared/routes';
import { BuildingIcon, CommentIcon, HousesIcon, PersonIcon, StaffIcon, WarningIcon } from '@/shared/ui';

import './HomePage.css';

interface StatCardProps {
  label: string;
  value: number | undefined;
  isLoading: boolean;
  icon: ReactNode;
}

function StatCard({ label, value, isLoading, icon }: StatCardProps) {
  return (
    <div className="card stat-card dashboard-stat">
      <div className="dashboard-stat__icon">{icon}</div>
      <div className="stat-card__label dashboard-stat__label">{label}</div>
      <div className="stat-card__value">{isLoading ? '—' : (value ?? 0)}</div>
    </div>
  );
}

function OrganizationOverview() {
  const { data: principal } = useMe();
  const organizations = useOrganizations();
  const staff = useStaffList();
  const residents = useResidents();
  const incidents = useIncidents();
  const houses = useHouseManagement();

  return (
    <div className="stat-grid">
      {canBrowseOrganizations(principal) && (
        <StatCard label="Организации" value={organizations.data?.length} isLoading={organizations.isLoading} icon={<BuildingIcon />} />
      )}
      <StatCard label="Дома в управлении" value={houses.data?.length} isLoading={houses.isLoading} icon={<HousesIcon />} />
      <StatCard label="Сотрудники" value={staff.data?.length} isLoading={staff.isLoading} icon={<StaffIcon />} />
      <StatCard label="Жители" value={residents.data?.length} isLoading={residents.isLoading} icon={<PersonIcon />} />
      <StatCard label="Инциденты" value={incidents.data?.length} isLoading={incidents.isLoading} icon={<WarningIcon />} />
    </div>
  );
}

function AuthorityOverview({ organizationId }: { organizationId: string }) {
  const organization = useOrganization(organizationId);
  const summary = useTerritorySummary(organization.data?.territory_id ?? null);
  const total = summary.data?.total;
  const isLoading = organization.isLoading || summary.isLoading;

  return (
    <>
      <div className="stat-grid">
        <StatCard label="Дома на территории" value={total?.houses} isLoading={isLoading} icon={<HousesIcon />} />
        <StatCard label="Жители в приложении" value={total?.residents} isLoading={isLoading} icon={<PersonIcon />} />
        <StatCard label="Обращения в работе" value={total?.reports_open} isLoading={isLoading} icon={<CommentIcon />} />
        <StatCard label="Открытые инциденты" value={total?.incidents_open} isLoading={isLoading} icon={<WarningIcon />} />
        <StatCard label="УК и ТСЖ" value={total?.managing_organizations} isLoading={isLoading} icon={<BuildingIcon />} />
      </div>
      <Link className="btn btn--ghost dashboard-more" to={ROUTES.analytics}>
        Подробная статистика по территории
      </Link>
    </>
  );
}

export function HomePage() {
  const { data: principal } = useMe();
  const { data: me } = useProfile();

  const role = primaryRole(principal);
  const scopeNote = isAdmin(principal)
    ? 'Данные по всем городам и организациям'
    : isAuthority(principal)
      ? 'Данные по территории вашего органа власти'
      : 'Данные в рамках вашей организации';

  return (
    <>
      <section className="dashboard-hero">
        <div className="dashboard-hero__content">
          <div className="dashboard-hero__eyebrow">Операционный центр</div>
          <h1>{me?.display_name ? `Здравствуйте, ${me.display_name}` : 'Обзор'}</h1>
          <p>
            {[role && roleLabel(role), me?.organization_name].filter(Boolean).join(' · ') || scopeNote}
          </p>
          {me?.organization_name && <p className="dashboard-hero__note">{scopeNote}</p>}
        </div>
      </section>

      {isAuthority(principal) && principal?.organization_id ? (
        <AuthorityOverview organizationId={principal.organization_id} />
      ) : (
        principal && <OrganizationOverview />
      )}
    </>
  );
}
