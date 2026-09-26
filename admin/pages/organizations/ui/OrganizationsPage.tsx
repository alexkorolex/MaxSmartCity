import { useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';

import { useCities } from '@/entities/geo';
import { AUTHORITY_KIND_LABELS, ORGANIZATION_TYPE_LABELS, useOrganizations, type Organization } from '@/entities/organization';
import { canBrowseOrganizations, isAdmin, useMe } from '@/entities/session';
import { useTerritories } from '@/entities/territory';
import { RegisterAuthorityForm } from '@/features/register-authority';
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
  const [registering, setRegistering] = useState<'housing' | 'authority' | null>(null);
  const territories = useTerritories();
  const territoryNames = useMemo(
    () => new Map((territories.data ?? []).map((node) => [node.id, node.name])),
    [territories.data],
  );

  const filtered = useMemo(() => (data ?? []).filter((org) => !city || org.city === city), [data, city]);

  function kindLabel(org: Organization): string {
    return org.authority_kind ? AUTHORITY_KIND_LABELS[org.authority_kind] : ORGANIZATION_TYPE_LABELS[org.type];
  }

  return (
    <>
      {registering === 'authority' && (
        <div className="card">
          <div className="card__header">
            <div>
              <div className="card__title">Регистрация органа власти</div>
              <div className="card__meta">
                Администрация города, района, префектура, управа или МО — вместе с первым сотрудником. Орган видит
                статистику и инциденты своей территории, публикует новости её жителям.
              </div>
            </div>
          </div>
          <div className="card__body">
            <RegisterAuthorityForm
              onCancel={() => setRegistering(null)}
              onRegistered={(organizationId, registration) => {
                setRegistering(null);
                navigate(ROUTES.organization(organizationId), { state: { registration } });
              }}
            />
          </div>
        </div>
      )}

      {registering === 'housing' && (
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
              onCancel={() => setRegistering(null)}
              onRegistered={(organizationId, registration) => {
                setRegistering(null);
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
            <div className="card__meta">Органы власти, управляющие компании, ТСЖ и городские службы</div>
          </div>
          {isAdmin(principal) && !registering && (
            <div className="form-actions">
              <button type="button" className="btn btn--ghost" onClick={() => setRegistering('authority')}>
                Орган власти
              </button>
              <button type="button" className="btn" onClick={() => setRegistering('housing')}>
                УК / ТСЖ
              </button>
            </div>
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
                        <td className="cell-secondary" data-label="Тип">
                          {kindLabel(org)}
                          {org.territory_id && territoryNames.has(org.territory_id) && (
                            <div className="cell-muted">{territoryNames.get(org.territory_id)}</div>
                          )}
                        </td>
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
