import { useHouseManagement, useTerminateHouseManagement } from '@/entities/geo';
import { canBrowseOrganizations, useMe } from '@/entities/session';
import { TakeHouseForm } from '@/features/take-house';
import { formatCalendarDate } from '@/shared/lib';
import { AsyncState, EmptyState, HousesIcon, Pill } from '@/shared/ui';

import './HousesPage.css';

export function HousesPage() {
  const { data: principal } = useMe();
  const isAuthority = canBrowseOrganizations(principal);
  const hasOrganization = Boolean(principal?.organization_id);
  const houses = useHouseManagement();
  const terminate = useTerminateHouseManagement();
  const canTake = isAuthority || hasOrganization;

  return (
    <>
      <div className="card">
        <div className="card__header">
          <div>
            <div className="card__title">Дома в управлении</div>
            <div className="card__meta">
              {isAuthority
                ? 'Какая УК или ТСЖ обслуживает каждый дом'
                : 'Дома вашей организации — по ним вы видите жителей, их заявки и инциденты'}
            </div>
          </div>
        </div>
        <div className="card__body card__body--flush">
          <AsyncState isLoading={houses.isLoading} error={houses.error} onRetry={() => void houses.refetch()}>
            {!houses.data || houses.data.length === 0 ? (
              <EmptyState icon={<HousesIcon />} title="Домов пока нет" />
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Адрес</th>
                      {isAuthority && <th>Организация</th>}
                      <th>Основание</th>
                      <th>С</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {houses.data.map((item) => (
                      <tr key={item.id}>
                        <td className="houses-page__address" data-label="Адрес">
                          <div className="cell-primary">{item.house_formatted}</div>
                          {item.assigned_via_reserve_registry && <Pill tone="info" label="Из Перечня" />}
                        </td>
                        {isAuthority && (
                          <td className="cell-secondary" data-label="Организация">{item.organization_name}</td>
                        )}
                        <td className="cell-muted" data-label="Основание">{item.basis ?? '—'}</td>
                        <td className="cell-muted" data-label="С">
                          {formatCalendarDate(item.effective_from, { year: true, fallback: '—' })}
                        </td>
                        <td data-label="Действия">
                          <button
                            type="button"
                            className="btn btn--danger-ghost btn--small"
                            disabled={terminate.isPending}
                            onClick={() => {
                              if (window.confirm(`Снять дом «${item.house_formatted}» с управления?`)) {
                                terminate.mutate({ managementId: item.id });
                              }
                            }}
                          >
                            Снять с управления
                          </button>
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

      <div className="card">
        <div className="card__header">
          <div>
            <div className="card__title">Взять дом в управление</div>
            <div className="card__meta">
              {isAuthority
                ? 'Назначьте дом УК или ТСЖ — в том числе из Перечня, если собственники не выбрали управляющую организацию'
                : 'Найдите дом по адресу. Дом, который уже обслуживает другая организация, передаётся только через управу'}
            </div>
          </div>
        </div>
        <div className="card__body">
          {canTake ? (
            <TakeHouseForm />
          ) : (
            <EmptyState icon={<HousesIcon />} title="Вы не привязаны к организации" />
          )}
        </div>
      </div>
    </>
  );
}
