import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useCities } from '@/entities/geo';
import { INCIDENT_STATUS_LABELS, INCIDENT_STATUS_TONES, useIncidents } from '@/entities/incident';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { AsyncState, CitySelect, EmptyState, Pill, WarningIcon } from '@/shared/ui';

export function IncidentsPage() {
  const [city, setCity] = useState('');
  const navigate = useNavigate();

  const { data: cities } = useCities();
  const { data, isLoading, error, refetch } = useIncidents(city || undefined);

  return (
    <div className="card">
      <div className="card__header">
        <div>
          <div className="card__title">Инциденты</div>
          <div className="card__meta">Инциденты, связанные с заявками жителей</div>
        </div>
      </div>
      <div className="filter-bar">
        <CitySelect cities={cities ?? []} value={city} onChange={setCity} />
      </div>
      <div className="card__body card__body--flush">
        <AsyncState isLoading={isLoading} error={error} onRetry={() => void refetch()}>
          {!data || data.length === 0 ? (
            <EmptyState icon={<WarningIcon />} title="Инцидентов не найдено" />
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Название</th>
                    <th>Статус</th>
                    <th>Первое обращение</th>
                    <th>Последнее обращение</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((incident) => (
                    <tr
                      key={incident.id}
                      className="is-clickable"
                      role="link"
                      tabIndex={0}
                      onClick={() => navigate(ROUTES.incident(incident.id))}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') navigate(ROUTES.incident(incident.id));
                      }}
                    >
                      <td className="cell-primary" data-label="Название">{incident.title}</td>
                      <td data-label="Статус">
                        <Pill
                          tone={INCIDENT_STATUS_TONES[incident.status]}
                          label={INCIDENT_STATUS_LABELS[incident.status]}
                        />
                      </td>
                      <td className="cell-muted" data-label="Первое обращение">{formatDateTime(incident.first_report_at)}</td>
                      <td className="cell-muted" data-label="Последнее обращение">{formatDateTime(incident.last_report_at)}</td>
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
