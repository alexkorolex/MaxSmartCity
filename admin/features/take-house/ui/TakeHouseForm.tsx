import { useMemo, useState, type FormEvent } from 'react';

import { HouseSearchField, useAssignHouseManagement, type House } from '@/entities/geo';
import { HOUSING_ORGANIZATION_TYPES, useOrganizations } from '@/entities/organization';
import { canBrowseOrganizations, useMe } from '@/entities/session';
import { apiErrorMessage } from '@/shared/lib';

import './TakeHouseForm.css';

export function TakeHouseForm() {
  const { data: principal } = useMe();
  const isAuthority = canBrowseOrganizations(principal);
  const organizations = useOrganizations();
  const assign = useAssignHouseManagement();

  const [house, setHouse] = useState<House | null>(null);
  const [organizationId, setOrganizationId] = useState('');
  const [basis, setBasis] = useState('');
  const [viaReserveRegistry, setViaReserveRegistry] = useState(false);
  const [lastAdded, setLastAdded] = useState('');

  const housingOrganizations = useMemo(
    () =>
      (organizations.data ?? []).filter(
        (org) => org.enabled && (HOUSING_ORGANIZATION_TYPES as string[]).includes(org.type),
      ),
    [organizations.data],
  );
  const targetOrganizationId = isAuthority ? organizationId : (principal?.organization_id ?? '');
  const targetOrganization = housingOrganizations.find((org) => org.id === targetOrganizationId);
  const canUseReserveRegistry = isAuthority && Boolean(targetOrganization?.in_reserve_registry);

  function isSelectable(candidate: House): boolean {
    if (!candidate.managed_by_organization_id) return true;
    return isAuthority && candidate.managed_by_organization_id !== targetOrganizationId;
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!house || !targetOrganizationId || !basis.trim()) return;
    assign.mutate(
      {
        house_id: house.house_id,
        organization_id: targetOrganizationId,
        basis: basis.trim(),
        assigned_via_reserve_registry: canUseReserveRegistry && viaReserveRegistry,
      },
      {
        onSuccess: (management) => {
          setLastAdded(management.house_formatted);
          setHouse(null);
          setBasis('');
          setViaReserveRegistry(false);
        },
      },
    );
  }

  return (
    <form className="take-house" onSubmit={handleSubmit}>
      {isAuthority && (
        <div className="form-grid">
          <div className="form-grid__wide">
            <label className="field-label" htmlFor="take-house-organization">
              Организация
            </label>
            <select
              id="take-house-organization"
              className="field"
              value={organizationId}
              onChange={(event) => {
                setOrganizationId(event.target.value);
                setViaReserveRegistry(false);
              }}
            >
              <option value="">Выберите УК или ТСЖ</option>
              {housingOrganizations.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                  {org.city ? ` · ${org.city}` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      <HouseSearchField value={house} onChange={setHouse} isDisabled={(candidate) => !isSelectable(candidate)} />

      {house && (
        <div className="form-grid">
          <div className="form-grid__wide">
            <label className="field-label" htmlFor="take-house-basis">
              Основание
            </label>
            <input
              id="take-house-basis"
              className="field"
              placeholder="Договор управления № … от … / протокол общего собрания № …"
              value={basis}
              onChange={(event) => setBasis(event.target.value)}
            />
            {house.managed_by_organization_name && (
              <div className="form-hint">
                Дом будет передан от «{house.managed_by_organization_name}» — прежнее управление завершится.
              </div>
            )}
          </div>
          {canUseReserveRegistry && (
            <label className="checkbox-field form-grid__wide">
              <input
                type="checkbox"
                checked={viaReserveRegistry}
                onChange={(event) => setViaReserveRegistry(event.target.checked)}
              />
              Назначена из Перечня (собственники не выбрали способ управления)
            </label>
          )}
        </div>
      )}

      {assign.isError && <div className="form-error">{apiErrorMessage(assign.error)}</div>}
      {lastAdded && !house && <div className="form-success">Дом «{lastAdded}» добавлен в управление.</div>}
      <div className="form-actions">
        <button
          type="submit"
          className="btn"
          disabled={!house || !targetOrganizationId || !basis.trim() || assign.isPending}
        >
          {assign.isPending ? 'Сохраняем…' : 'Взять в управление'}
        </button>
      </div>
    </form>
  );
}
