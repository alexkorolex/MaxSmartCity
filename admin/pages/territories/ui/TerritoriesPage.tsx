import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { isAdmin, isAuthority, useMe } from '@/entities/session';
import { TERRITORY_TYPE_LABELS, territoryPath, useTerritories } from '@/entities/territory';
import { StreetAssignment, TerritoryEditor, TerritoryTree } from '@/features/manage-territories';
import { ROUTES } from '@/shared/routes';
import { AsyncState } from '@/shared/ui';

import './TerritoriesPage.css';

export function TerritoriesPage() {
  const { data: principal } = useMe();
  const canAddCity = isAdmin(principal);
  const editable = canAddCity || isAuthority(principal);
  const territories = useTerritories();
  const nodes = useMemo(() => territories.data ?? [], [territories.data]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pendingName, setPendingName] = useState<{ parentId: string; name: string } | null>(null);

  useEffect(() => {
    if (!selectedId && nodes.length > 0) setSelectedId(nodes.find((node) => node.parent_id === null)?.id ?? null);
  }, [nodes, selectedId]);

  useEffect(() => {
    if (!pendingName) return;
    const created = nodes.find((node) => node.parent_id === pendingName.parentId && node.name === pendingName.name);
    if (created) {
      setSelectedId(created.id);
      setPendingName(null);
    }
  }, [nodes, pendingName]);

  const selected = nodes.find((node) => node.id === selectedId) ?? null;
  const path = selected ? territoryPath(nodes, selected.id) : [];
  const rootId = path[0]?.id ?? null;

  return (
    <AsyncState isLoading={territories.isLoading} error={territories.error} onRetry={() => void territories.refetch()}>
      <div className="territories-layout">
        <section className="card territories-layout__tree">
          <div className="card__header">
            <div>
              <div className="card__title">Территории</div>
              <div className="card__meta">
                {canAddCity
                  ? 'Город и его деления — округа, районы, муниципальные образования'
                  : 'Территория вашего органа власти: добавляйте деления и распределяйте по ним дома'}
              </div>
            </div>
          </div>
          <div className="card__body">
            <TerritoryTree nodes={nodes} selectedId={selectedId} onSelect={setSelectedId} canAddCity={canAddCity} />
          </div>
        </section>

        {selected && (
          <div className="territories-layout__detail">
            <section className="card">
              <div className="card__header">
                <div>
                  <div className="territory-path">{path.slice(0, -1).map((node) => node.name).join(' / ')}</div>
                  <div className="card__title">{selected.name}</div>
                  <div className="card__meta">
                    {TERRITORY_TYPE_LABELS[selected.type]} · домов: {selected.house_count.toLocaleString('ru-RU')}
                    {selected.id === rootId && selected.direct_house_count > 0 && selected.house_count !== selected.direct_house_count
                      ? ` · не распределено: ${selected.direct_house_count.toLocaleString('ru-RU')}`
                      : ''}
                  </div>
                </div>
                <Link className="btn btn--ghost btn--small" to={`${ROUTES.analytics}?territory=${selected.id}`}>
                  Статистика
                </Link>
              </div>
              <div className="card__body territory-detail">
                <div>
                  <div className="field-label">Органы власти</div>
                  {selected.authorities.length > 0 ? (
                    <ul className="territory-detail__authorities">
                      {selected.authorities.map((name) => (
                        <li key={name}>{name}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="cell-muted">
                      Не назначены.{canAddCity && ' Зарегистрируйте орган власти в разделе «Организации».'}
                    </p>
                  )}
                </div>
                {editable && (
                  <TerritoryEditor
                    key={selected.id}
                    node={selected}
                    onCreated={(name) => setPendingName({ parentId: selected.id, name })}
                    onDeleted={(parentId) => setSelectedId(parentId)}
                  />
                )}
              </div>
            </section>

            {editable && rootId && (
              <section className="card">
                <div className="card__header">
                  <div>
                    <div className="card__title">Дома по улицам</div>
                    <div className="card__meta">
                      Отметьте улицы и отнесите их к «{selected.name}». Если улица делится между районами —
                      раскройте её и выберите дома.
                    </div>
                  </div>
                </div>
                <div className="card__body">
                  <StreetAssignment key={selected.id} territory={selected} rootId={rootId} />
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </AsyncState>
  );
}
