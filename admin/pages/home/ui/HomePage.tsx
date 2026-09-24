import { useHouseManagement } from '@/entities/geo';
import { useIncidents } from '@/entities/incident';
import { useOrganizations } from '@/entities/organization';
import { useResidents } from '@/entities/resident';
import { canBrowseOrganizations, isAdmin, roleLabel, useMe } from '@/entities/session';
import { useStaffList } from '@/entities/staff';
import { BuildingIcon, HousesIcon, PersonIcon, StaffIcon, WarningIcon } from '@/shared/ui';

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

export function HomePage() {
  const { data: principal } = useMe();
  const organizations = useOrganizations();
  const staff = useStaffList();
  const residents = useResidents();
  const incidents = useIncidents();
  const houses = useHouseManagement();

  return (
    <>
      <section className="dashboard-hero">
        <div className="dashboard-hero__content">
          <div className="dashboard-hero__eyebrow">Операционный центр</div>
          <h1>
              {principal && isAdmin(principal)
                ? 'Обзор платформы'
                : `Обзор — ${principal ? roleLabel(principal.roles[0] ?? '') : ''}`}
          </h1>
          <p>
              {principal && isAdmin(principal)
                ? 'Данные по всем городам и организациям'
                : 'Данные в рамках вашей организации'}
          </p>
        </div>
        <div className="dashboard-hero__pulse" aria-hidden="true"><span /></div>
      </section>

      <div className="stat-grid">
        {canBrowseOrganizations(principal) && (
          <StatCard label="Организации" value={organizations.data?.length} isLoading={organizations.isLoading} icon={<BuildingIcon />} />
        )}
        <StatCard label="Дома в управлении" value={houses.data?.length} isLoading={houses.isLoading} icon={<HousesIcon />} />
        <StatCard label="Сотрудники" value={staff.data?.length} isLoading={staff.isLoading} icon={<StaffIcon />} />
        <StatCard label="Жители" value={residents.data?.length} isLoading={residents.isLoading} icon={<PersonIcon />} />
        <StatCard label="Инциденты" value={incidents.data?.length} isLoading={incidents.isLoading} icon={<WarningIcon />} />
      </div>
    </>
  );
}
import type { ReactNode } from 'react';
