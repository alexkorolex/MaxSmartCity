import { useMemo, useState } from 'react';

import { useOrganizations } from '@/entities/organization';
import { roleLabel } from '@/entities/session';
import { useStaffList } from '@/entities/staff';
import { AsyncState, CitySelect, EmptyState, Pill, StaffIcon } from '@/shared/ui';

export function StaffPage() {
  const [city, setCity] = useState('');
  const [organizationId, setOrganizationId] = useState('');

  const { data: organizations } = useOrganizations();
  const { data, isLoading, error, refetch } = useStaffList(city || undefined, organizationId || undefined);

  const cities = useMemo(() => {
    const set = new Set<string>();
    for (const org of organizations ?? []) if (org.city) set.add(org.city);
    return [...set].sort();
  }, [organizations]);

  const orgOptions = useMemo(
    () => (organizations ?? []).filter((org) => !city || org.city === city),
    [organizations, city],
  );

  return (
    <div className="card">
      <div className="card__header">
        <div>
          <div className="card__title">Сотрудники</div>
          <div className="card__meta">Администраторы, управы и жилищники</div>
        </div>
      </div>
      <div className="filter-bar">
        <CitySelect
          cities={cities}
          value={city}
          onChange={(next) => {
            setCity(next);
            setOrganizationId('');
          }}
        />
        <div className="filter-bar__field">
          <span className="filter-bar__label">Организация</span>
          <select
            className="field"
            value={organizationId}
            onChange={(event) => setOrganizationId(event.target.value)}
          >
            <option value="">Все организации</option>
            {orgOptions.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="card__body" style={{ padding: 0 }}>
        <AsyncState isLoading={isLoading} error={error} onRetry={() => void refetch()}>
          {!data || data.length === 0 ? (
            <EmptyState icon={<StaffIcon />} title="Сотрудников не найдено" />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Сотрудник</th>
                    <th>Роль</th>
                    <th>Организация</th>
                    <th>Город</th>
                    <th>Статус</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((member) => (
                    <tr key={member.id}>
                      <td>
                        <div className="cell-primary">{member.display_name}</div>
                        <div className="cell-muted">{member.login}</div>
                      </td>
                      <td className="cell-secondary">
                        {member.role_code ? roleLabel(member.role_code) : '—'}
                      </td>
                      <td className="cell-secondary">{member.organization_name ?? '—'}</td>
                      <td className="cell-secondary">{member.organization_city ?? '—'}</td>
                      <td>
                        <Pill
                          tone={member.is_active ? 'success' : 'neutral'}
                          label={member.is_active ? 'Активен' : 'Отключён'}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </AsyncState>
      </div>
    </div>
  );
}
