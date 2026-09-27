import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useCities } from '@/entities/geo';
import { useResidents } from '@/entities/resident';
import { isAdmin, useMe } from '@/entities/session';
import { formatCalendarDate } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, CitySelect, EmptyState, PersonIcon } from '@/shared/ui';

export function ResidentsPage() {
  const [city, setCity] = useState('');
  const navigate = useNavigate();

  const { data: principal } = useMe();
  const showCityFilter = isAdmin(principal);
  const { data: cities } = useCities();
  const { data, isLoading, error, refetch } = useResidents(city || undefined);

  return (
    <div className="card">
      <div className="card__header">
        <div>
          <div className="card__title">Жители</div>
          <div className="card__meta">Жители и количество оставленных ими заявок</div>
        </div>
      </div>
      {showCityFilter && (
        <div className="filter-bar">
          <CitySelect cities={cities ?? []} value={city} onChange={setCity} />
        </div>
      )}
      <div className="card__body card__body--flush">
        <AsyncState isLoading={isLoading} error={error} onRetry={() => void refetch()}>
          {!data || data.length === 0 ? (
            <EmptyState icon={<PersonIcon />} title="Жителей не найдено" />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Житель</th>
                    <th>Дом</th>
                    <th>Город</th>
                    <th>Заявок</th>
                    <th>В системе с</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((resident) => (
                    <tr
                      key={resident.id}
                      className="is-clickable"
                      role="link"
                      tabIndex={0}
                      onClick={() => navigate(ROUTES.resident(resident.id))}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') navigate(ROUTES.resident(resident.id));
                      }}
                    >
                      <td data-label="Житель">
                        <div className="cell-primary">{resident.display_name ?? 'Без имени'}</div>
                        {resident.username && <div className="cell-muted">@{resident.username}</div>}
                      </td>
                      <td className="cell-secondary" data-label="Дом">{resident.house_formatted ?? '—'}</td>
                      <td className="cell-secondary" data-label="Город">{resident.house_city ?? '—'}</td>
                      <td className="cell-primary" data-label="Заявок">{resident.reports_count}</td>
                      <td className="cell-muted" data-label="В системе с">{formatCalendarDate(resident.created_at, { year: true })}</td>
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
