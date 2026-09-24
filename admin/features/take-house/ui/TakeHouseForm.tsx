import { useMemo, useState, type FormEvent } from 'react';

import { useAssignHouseManagement, useCities, useHouseSearch, type House } from '@/entities/geo';
import { HOUSING_ORGANIZATION_TYPES, useOrganizations } from '@/entities/organization';
import { canBrowseOrganizations, useMe } from '@/entities/session';
import { apiErrorMessage } from '@/shared/lib';

import './TakeHouseForm.css';

/**
 * Attach a house to a management company / HOA. A housing worker takes a house nobody
 * manages yet for their own organization; the admin and the district administration pick
 * any housing organization and may also move a house away from its current manager
 * (e.g. appointing a УК from the Перечень).
 */
export function TakeHouseForm() {
  const { data: principal } = useMe();
  const isAuthority = canBrowseOrganizations(principal);
  const organizations = useOrganizations();
  const { data: cities } = useCities();
  const assign = useAssignHouseManagement();

  const [query, setQuery] = useState('');
  const [city, setCity] = useState('');
  const [house, setHouse] = useState<House | null>(null);
  const [organizationId, setOrganizationId] = useState('');
  const [basis, setBasis] = useState('');
  const [viaReserveRegistry, setViaReserveRegistry] = useState(false);
  const [lastAdded, setLastAdded] = useState('');
  const search = useHouseSearch(query, city);

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
      <div className="form-grid">
        {isAuthority && (
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
        )}
        <div>
          <label className="field-label" htmlFor="take-house-query">
            Адрес
          </label>
          <input
            id="take-house-query"
            className="field"
            placeholder="Улица и номер дома"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setHouse(null);
            }}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="take-house-city">
            Город
          </label>
          <select id="take-house-city" className="field" value={city} onChange={(event) => setCity(event.target.value)}>
            <option value="">Все города</option>
            {(cities ?? []).map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
      </div>

      {query.trim().length >= 2 && (
        <div className="take-house__results" role="listbox" aria-label="Найденные дома">
          {search.isLoading && <div className="take-house__hint">Ищем…</div>}
          {search.data?.length === 0 && <div className="take-house__hint">Ничего не найдено</div>}
          {search.data?.map((candidate) => {
            const selectable = isSelectable(candidate);
            const selected = house?.house_id === candidate.house_id;
            return (
              <button
                key={candidate.house_id}
                type="button"
                role="option"
                aria-selected={selected}
                className={`take-house__option${selected ? ' take-house__option--selected' : ''}`}
                disabled={!selectable}
                onClick={() => setHouse(candidate)}
              >
                <span className="take-house__address">{candidate.formatted}</span>
                <span className="take-house__manager">
                  {candidate.managed_by_organization_name
                    ? `Обслуживает: ${candidate.managed_by_organization_name}`
                    : 'Свободен'}
                </span>
              </button>
            );
          })}
        </div>
      )}

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
