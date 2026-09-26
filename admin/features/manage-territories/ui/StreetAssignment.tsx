import { useMemo, useState } from 'react';

import {
  useAssignToTerritory,
  useTerritoryStreetHouses,
  useTerritoryStreets,
  type TerritoryNode,
  type TerritoryStreet,
} from '@/entities/territory';
import { apiErrorMessage } from '@/shared/lib';
import { AsyncState, EmptyState, HousesIcon } from '@/shared/ui';

import './ManageTerritories.css';

function StreetHouses({ territory, street }: { territory: TerritoryNode; street: string }) {
  const houses = useTerritoryStreetHouses(territory.id, street);
  const assign = useAssignToTerritory();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  function toggle(houseId: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(houseId)) next.delete(houseId);
      else next.add(houseId);
      return next;
    });
  }

  return (
    <div className="street-houses">
      <AsyncState isLoading={houses.isLoading} error={houses.error}>
        <ul className="street-houses__list">
          {(houses.data ?? []).map((house) => (
            <li key={house.house_id}>
              <label className="street-houses__item">
                <input
                  type="checkbox"
                  checked={selected.has(house.house_id)}
                  onChange={() => toggle(house.house_id)}
                />
                <span className="street-houses__number">{house.house_number ?? house.formatted}</span>
                <span className={house.territory_id === territory.id ? 'street-houses__here' : 'cell-muted'}>
                  {house.territory_name}
                </span>
              </label>
            </li>
          ))}
        </ul>
        <div className="form-actions">
          <button
            type="button"
            className="btn btn--small"
            disabled={selected.size === 0 || assign.isPending}
            onClick={() =>
              assign.mutate(
                { id: territory.id, payload: { house_ids: [...selected] } },
                { onSuccess: () => setSelected(new Set()) },
              )
            }
          >
            Отнести {selected.size || ''} к «{territory.name}»
          </button>
          {assign.isError && <span className="form-hint form-hint--error">{apiErrorMessage(assign.error)}</span>}
        </div>
      </AsyncState>
    </div>
  );
}

function StreetRow({
  street,
  territory,
  checked,
  expanded,
  onToggle,
  onExpand,
}: {
  street: TerritoryStreet;
  territory: TerritoryNode;
  checked: boolean;
  expanded: boolean;
  onToggle: () => void;
  onExpand: () => void;
}) {
  const inHere = street.territories.find((share) => share.territory_id === territory.id)?.house_count ?? 0;
  return (
    <li className={`street-row${inHere === street.house_count ? ' street-row--done' : ''}`}>
      <div className="street-row__main">
        <input type="checkbox" aria-label={`Выбрать ${street.street}`} checked={checked} onChange={onToggle} />
        <button type="button" className="street-row__name" aria-expanded={expanded} onClick={onExpand}>
          {street.street}
        </button>
        <span className="street-row__count">{street.house_count}</span>
      </div>
      <div className="street-row__shares">
        {street.territories.map((share) => (
          <span
            key={share.territory_id}
            className={`street-share${share.territory_id === territory.id ? ' street-share--here' : ''}`}
          >
            {share.territory_name} · {share.house_count}
          </span>
        ))}
      </div>
      {expanded && <StreetHouses territory={territory} street={street.street} />}
    </li>
  );
}

export function StreetAssignment({ territory, rootId }: { territory: TerritoryNode; rootId: string }) {
  const [query, setQuery] = useState('');
  const [onlyUnassigned, setOnlyUnassigned] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<string | null>(null);
  const streets = useTerritoryStreets(territory.id, query);
  const assign = useAssignToTerritory();
  const isRoot = territory.id === rootId;

  const visible = useMemo(
    () =>
      (streets.data ?? []).filter(
        (street) => !onlyUnassigned || street.territories.some((share) => share.territory_id === rootId),
      ),
    [streets.data, onlyUnassigned, rootId],
  );

  function toggle(street: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(street)) next.delete(street);
      else next.add(street);
      return next;
    });
  }

  return (
    <div className="street-assignment">
      <div className="street-assignment__toolbar">
        <input
          className="field"
          type="search"
          placeholder="Поиск улицы"
          aria-label="Поиск улицы"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <label className="checkbox-field">
          <input type="checkbox" checked={onlyUnassigned} onChange={(event) => setOnlyUnassigned(event.target.checked)} />
          Только неразмеченные
        </label>
      </div>
      <div className="street-assignment__actions">
        <button
          type="button"
          className="btn"
          disabled={selected.size === 0 || assign.isPending}
          onClick={() =>
            assign.mutate(
              { id: territory.id, payload: { streets: [...selected] } },
              { onSuccess: () => setSelected(new Set()) },
            )
          }
        >
          {isRoot ? `Вернуть на уровень «${territory.name}»` : `Отнести к «${territory.name}»`}
          {selected.size > 0 && ` · ${selected.size}`}
        </button>
        {selected.size > 0 && (
          <button type="button" className="btn btn--ghost" onClick={() => setSelected(new Set())}>
            Снять выбор
          </button>
        )}
        {assign.isSuccess && <span className="form-hint">Перенесено домов: {assign.data.moved}</span>}
        {assign.isError && <span className="form-hint form-hint--error">{apiErrorMessage(assign.error)}</span>}
      </div>
      <AsyncState isLoading={streets.isLoading} error={streets.error}>
        {visible.length === 0 ? (
          <EmptyState icon={<HousesIcon />} title="Улиц не найдено" />
        ) : (
          <ul className="street-assignment__list">
            {visible.map((street) => (
              <StreetRow
                key={street.street}
                street={street}
                territory={territory}
                checked={selected.has(street.street)}
                expanded={expanded === street.street}
                onToggle={() => toggle(street.street)}
                onExpand={() => setExpanded((current) => (current === street.street ? null : street.street))}
              />
            ))}
          </ul>
        )}
      </AsyncState>
    </div>
  );
}
