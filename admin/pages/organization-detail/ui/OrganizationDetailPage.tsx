import { Link, useLocation, useParams } from 'react-router-dom';

import {
  CredentialsEmailNotice,
  ORGANIZATION_TYPE_LABELS,
  type OrganizationRegistrationResult,
  useDeactivateOrganizationMember,
  useOrganization,
  useOrganizationMembers,
} from '@/entities/organization';
import { canBrowseOrganizations, isAdmin, roleLabel, useMe } from '@/entities/session';
import { AddOrganizationEmployeeForm } from '@/features/add-organization-employee';
import { formatDateTime } from '@/shared/lib';
import { ROUTES } from '@/shared/routes';
import { ArrowLeftIcon, AsyncState, EmptyState, InboxIcon, Pill } from '@/shared/ui';

export function OrganizationDetailPage() {
  const { organizationId = '' } = useParams();
  const registration = (useLocation().state as { registration?: OrganizationRegistrationResult } | null)
    ?.registration;
  const organization = useOrganization(organizationId);
  const members = useOrganizationMembers(organizationId);
  const deactivate = useDeactivateOrganizationMember(organizationId);
  const { data: principal } = useMe();
  // The admin manages every roster; staff manage their own organization's colleagues.
  const canManage = isAdmin(principal) || principal?.organization_id === organizationId;
  const org = organization.data;

  return (
    <>
      {canBrowseOrganizations(principal) && (
        <div className="page-back">
          <Link to={ROUTES.organizations} className="btn btn--ghost btn--small">
            <ArrowLeftIcon width={16} height={16} />
            К списку организаций
          </Link>
        </div>
      )}

      {registration?.organization_id === organizationId && (
        <div className="card">
          <div className="card__body">
            <CredentialsEmailNotice result={registration.credentials_email} login={registration.employee.login} />
          </div>
        </div>
      )}

      <AsyncState
        isLoading={organization.isLoading}
        error={organization.error}
        onRetry={() => void organization.refetch()}
      >
        {org && (
          <div className="card">
            <div className="card__header">
              <div>
                <div className="card__title">{org.name}</div>
                <div className="card__meta">
                  {ORGANIZATION_TYPE_LABELS[org.type]}
                  {org.city ? ` · ${org.city}` : ''}
                </div>
              </div>
              <div className="detail-badges">
                {org.in_reserve_registry && <Pill tone="info" label="В Перечне ГИС ЖКХ" />}
                <Pill tone={org.enabled ? 'success' : 'neutral'} label={org.enabled ? 'Активна' : 'Отключена'} />
              </div>
            </div>
            <div className="card__body">
              <div className="stat-grid">
                <div className="stat-card">
                  <div className="stat-card__label">ИНН</div>
                  <div className="stat-card__value stat-card__value--compact">{org.inn ?? '—'}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-card__label">ОГРН</div>
                  <div className="stat-card__value stat-card__value--compact">{org.ogrn ?? '—'}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-card__label">Лицензия</div>
                  <div className="stat-card__value stat-card__value--compact">{org.license_number ?? '—'}</div>
                </div>
                <div className="stat-card">
                  <div className="stat-card__label">Код</div>
                  <div className="stat-card__value stat-card__value--compact">{org.code}</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </AsyncState>

      <div className="card">
        <div className="card__header">
          <div>
            <div className="card__title">Сотрудники</div>
            <div className="card__meta">
              Получают заявки жителей по домам организации. Уведомления в MAX приходят тем, кто привязал
              свой MAX-аккаунт.
            </div>
          </div>
        </div>
        <div className="card__body card__body--flush">
          <AsyncState isLoading={members.isLoading} error={members.error} onRetry={() => void members.refetch()}>
            {!members.data || members.data.length === 0 ? (
              <EmptyState icon={<InboxIcon />} title="Сотрудников пока нет" />
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Сотрудник</th>
                      <th>Роль</th>
                      <th>MAX</th>
                      <th>Добавлен</th>
                      <th>Статус</th>
                      {canManage && <th />}
                    </tr>
                  </thead>
                  <tbody>
                    {members.data.map((member) => (
                      <tr key={member.id}>
                        <td data-label="Сотрудник">
                          <div className="cell-primary">{member.display_name}</div>
                          <div className="cell-muted">
                            {member.login}
                            {member.email ? ` · ${member.email}` : ''}
                          </div>
                        </td>
                        <td className="cell-secondary" data-label="Роль">{roleLabel(member.role_code)}</td>
                        <td data-label="MAX">
                          <Pill
                            tone={member.has_max_account ? 'success' : 'neutral'}
                            label={member.has_max_account ? 'Привязан' : 'Не привязан'}
                          />
                        </td>
                        <td className="cell-muted" data-label="Добавлен">{formatDateTime(member.created_at)}</td>
                        <td data-label="Статус">
                          <Pill
                            tone={member.is_active ? 'success' : 'neutral'}
                            label={member.is_active ? 'Активен' : 'Отключён'}
                          />
                        </td>
                        {canManage && (
                          <td data-label="Действия">
                            {member.is_active && member.user_id !== principal?.actor_id && (
                              <button
                                type="button"
                                className="btn btn--ghost btn--small"
                                disabled={deactivate.isPending}
                                onClick={() => {
                                  if (window.confirm(`Отключить сотрудника «${member.display_name}» от организации?`)) {
                                    deactivate.mutate(member.id);
                                  }
                                }}
                              >
                                Отключить
                              </button>
                            )}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </AsyncState>
        </div>
      </div>

      {canManage && org && (
        <div className="card">
          <div className="card__header">
            <div>
              <div className="card__title">Новый сотрудник</div>
              <div className="card__meta">
                Учётная запись создаётся сразу в этой организации, логин и временный пароль придут коллеге на
                почту
              </div>
            </div>
          </div>
          <div className="card__body">
            <AddOrganizationEmployeeForm organizationId={org.id} />
          </div>
        </div>
      )}
    </>
  );
}
