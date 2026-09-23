import { useMemo, useState } from 'react';

import { useCities } from '@/entities/geo';
import { ORGANIZATION_TYPE_LABELS, useOrganizations } from '@/entities/organization';
import { AsyncState, CitySelect, EmptyState, InboxIcon, Pill } from '@/shared/ui';

export function OrganizationsPage() {
  const { data, isLoading, error, refetch } = useOrganizations();
  const { data: cities } = useCities();
  const [city, setCity] = useState('');

  const filtered = useMemo(() => (data ?? []).filter((org) => !city || org.city === city), [data, city]);

  return (
    <div className="card">
      <div className="card__header">
        <div>
          <div className="card__title">Организации</div>
          <div className="card__meta">Управы, водоканалы, энергосети и аварийные службы</div>
        </div>
      </div>
      <div className="filter-bar">
        <CitySelect cities={cities ?? []} value={city} onChange={setCity} />
      </div>
      <div className="card__body card__body--flush">
        <AsyncState isLoading={isLoading} error={error} onRetry={() => void refetch()}>
          {filtered.length === 0 ? (
            <EmptyState icon={<InboxIcon />} title="Организаций не найдено" />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Название</th>
                    <th>Тип</th>
                    <th>Город</th>
                    <th>Код</th>
                    <th>Статус</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((org) => (
                    <tr key={org.id}>
                      <td className="cell-primary" data-label="Название">{org.name}</td>
                      <td className="cell-secondary" data-label="Тип">{ORGANIZATION_TYPE_LABELS[org.type]}</td>
                      <td className="cell-secondary" data-label="Город">{org.city ?? '—'}</td>
                      <td className="cell-muted" data-label="Код">{org.code}</td>
                      <td data-label="Статус">
                        <Pill
                          tone={org.enabled ? 'success' : 'neutral'}
                          label={org.enabled ? 'Активна' : 'Отключена'}
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
