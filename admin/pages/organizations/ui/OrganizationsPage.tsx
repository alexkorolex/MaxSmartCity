import { useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { useCities } from '@/entities/geo';
import { ORGANIZATION_TYPE_LABELS, useOrganizations } from '@/entities/organization';
import { canBrowseOrganizations, isAdmin, useMe } from '@/entities/session';
import { RegisterOrganizationForm } from '@/features/register-organization';
import { ROUTES } from '@/shared/routes';
import { AsyncState, CitySelect, EmptyState, InboxIcon, Pill } from '@/shared/ui';

export function OrganizationsPage() {
  const { data: principal } = useMe();
  // A housing worker only ever sees their own organization - no directory of other УК/ТСЖ.
  if (principal && !canBrowseOrganizations(principal)) {
    if (principal.organization_id) return <Navigate to={ROUTES.organization(principal.organization_id)} replace />;
    return <EmptyState icon={<InboxIcon />} title="Вы не привязаны к организации" />;
  }
  return <OrganizationsDirectory />;
}

function OrganizationsDirectory() {
  const navigate = useNavigate();
  const { data, isLoading, error, refetch } = useOrganizations();
  const { data: cities } = useCities();
  const { data: principal } = useMe();
  const [city, setCity] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);

  const filtered = useMemo(() => (data ?? []).filter((org) => !city || org.city === city), [data, city]);

  return (
    <>
      {isRegistering && (
        <div className="card">
          <div className="card__header">
            <div>
              <div className="card__title">Регистрация управляющей организации</div>
              <div className="card__meta">
                УК или ТСЖ регистрируется сразу вместе с первым сотрудником — он получит логин и сможет
                принимать заявки жителей по домам организации.
              </div>
            </div>
          </div>
          <div className="card__body">
            <RegisterOrganizationForm
              onCancel={() => setIsRegistering(false)}
              onRegistered={(organizationId, registration) => {
                setIsRegistering(false);
                // The organization card tells the admin whether the credentials e-mail went out.
                navigate(ROUTES.organization(organizationId), { state: { registration } });
              }}
            />
          </div>
        </div>
      )}

      <div className="card">
        <div className="card__header">
          <div>
            <div className="card__title">Организации</div>
            <div className="card__meta">Управы, управляющие компании, ТСЖ и городские службы</div>
          </div>
          {isAdmin(principal) && !isRegistering && (
            <button type="button" className="btn" onClick={() => setIsRegistering(true)}>
              Зарегистрировать УК / ТСЖ
            </button>
          )}
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
                      <th>ИНН</th>
                      <th>Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((org) => (
                      <tr
                        key={org.id}
                        className="is-clickable"
                        tabIndex={0}
                        onClick={() => navigate(ROUTES.organization(org.id))}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter') navigate(ROUTES.organization(org.id));
                        }}
                      >
                        <td className="cell-primary" data-label="Название">{org.name}</td>
                        <td className="cell-secondary" data-label="Тип">{ORGANIZATION_TYPE_LABELS[org.type]}</td>
                        <td className="cell-secondary" data-label="Город">{org.city ?? '—'}</td>
                        <td className="cell-muted" data-label="ИНН">{org.inn ?? '—'}</td>
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
    </>
  );
}
