import { useMemo, useState } from 'react';

import { useCities } from '@/entities/geo';
import { HOUSING_ORGANIZATION_TYPES, useOrganizations } from '@/entities/organization';
import { isAuthority, roleLabel, useMe } from '@/entities/session';
import { useStaffList } from '@/entities/staff';
import { AsyncState, CitySelect, EmptyState, Pill, StaffIcon } from '@/shared/ui';
import { StaffDirectoryTable } from '@/widgets/staff-directory';

function ManagementStaffCard() {
  const { data: organizations } = useOrganizations();
  const [organizationId, setOrganizationId] = useState('');
  const managers = (organizations ?? []).filter((org) => (HOUSING_ORGANIZATION_TYPES as string[]).includes(org.type));

  return (
    <div className="card">
      <div className="card__header">
        <div>
          <div className="card__title">Сотрудники управляющих компаний</div>
          <div className="card__meta">УК и ТСЖ, которые управляют домами вашей территории</div>
        </div>
      </div>
      <div className="filter-bar">
        <div className="filter-bar__field">
          <label className="filter-bar__label" htmlFor="directory-organization">
            Управляющая компания
          </label>
          <select
            id="directory-organization"
            className="field"
            value={organizationId}
            onChange={(event) => setOrganizationId(event.target.value)}
          >
            <option value="">Все управляющие компании</option>
            {managers.map((org) => (
              <option key={org.id} value={org.id}>
                {org.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="card__body card__body--flush">
        <StaffDirectoryTable organizationId={organizationId || undefined} />
      </div>
    </div>
  );
}

export function StaffPage() {
  const { data: principal } = useMe();
  const authority = isAuthority(principal);
  const [city, setCity] = useState('');
  const [organizationId, setOrganizationId] = useState('');

  const { data: organizations } = useOrganizations();
  const { data: cities } = useCities();
  const { data, isLoading, error, refetch } = useStaffList(city || undefined, organizationId || undefined);

  const orgOptions = useMemo(
    () => (organizations ?? []).filter((org) => !city || org.city === city),
    [organizations, city],
  );

  return (
    <>
      <div className="card">
        <div className="card__header">
          <div>
            <div className="card__title">{authority ? 'Сотрудники вашей организации' : 'Сотрудники'}</div>
            <div className="card__meta">
              {authority ? 'Коллеги по органу власти' : 'Администраторы, органы власти и жилищники'}
            </div>
          </div>
        </div>
        {!authority && (
          <div className="filter-bar">
            <CitySelect
              cities={cities ?? []}
              value={city}
              onChange={(next) => {
                setCity(next);
                setOrganizationId('');
              }}
            />
            <div className="filter-bar__field">
              <label className="filter-bar__label" htmlFor="staff-organization">
                Организация
              </label>
              <select
                id="staff-organization"
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
        )}
        <div className="card__body card__body--flush">
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
                        <td data-label="Сотрудник">
                          <div className="cell-primary">{member.display_name}</div>
                          <div className="cell-muted">{member.login}</div>
                        </td>
                        <td className="cell-secondary" data-label="Роль">
                          {member.role_code ? roleLabel(member.role_code) : '—'}
                        </td>
                        <td className="cell-secondary" data-label="Организация">
                          {member.organization_name ?? '—'}
                        </td>
                        <td className="cell-secondary" data-label="Город">
                          {member.organization_city ?? '—'}
                        </td>
                        <td data-label="Статус">
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
      {authority && <ManagementStaffCard />}
    </>
  );
}
