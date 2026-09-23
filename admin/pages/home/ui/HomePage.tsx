import { useIncidents } from '@/entities/incident';
import { useOrganizations } from '@/entities/organization';
import { useResidents } from '@/entities/resident';
import { isAdmin, roleLabel, useMe } from '@/entities/session';
import { useStaffList } from '@/entities/staff';

function StatCard({ label, value, isLoading }: { label: string; value: number | undefined; isLoading: boolean }) {
  return (
    <div className="card stat-card">
      <div className="stat-card__label">{label}</div>
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

  return (
    <>
      <div className="card">
        <div className="card__header">
          <div>
            <div className="card__title">
              {principal && isAdmin(principal)
                ? 'Обзор платформы'
                : `Обзор — ${principal ? roleLabel(principal.roles[0] ?? '') : ''}`}
            </div>
            <div className="card__meta">
              {principal && isAdmin(principal)
                ? 'Данные по всем городам и организациям'
                : 'Данные в рамках вашей организации'}
            </div>
          </div>
        </div>
      </div>

      <div className="stat-grid">
        <StatCard label="Организации" value={organizations.data?.length} isLoading={organizations.isLoading} />
        <StatCard label="Сотрудники" value={staff.data?.length} isLoading={staff.isLoading} />
        <StatCard label="Жители" value={residents.data?.length} isLoading={residents.isLoading} />
        <StatCard label="Инциденты" value={incidents.data?.length} isLoading={incidents.isLoading} />
      </div>
    </>
  );
}
