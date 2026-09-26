import { useEffect, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';

import { useTerritorySummary, type TerritoryBreakdown, type TerritoryStats } from '@/entities/analytics';
import { isAdmin, useMe } from '@/entities/session';
import { flattenTerritoryTree, TERRITORY_TYPE_LABELS, useTerritories, type TerritoryType } from '@/entities/territory';
import { AsyncState, EmptyState, HousesIcon } from '@/shared/ui';

import './AnalyticsPage.css';

const number = new Intl.NumberFormat('ru-RU');

type Column = { key: keyof TerritoryStats; label: string };

const COLUMNS: Column[] = [
  { key: 'houses', label: 'Дома' },
  { key: 'residents', label: 'Жители' },
  { key: 'reports_open', label: 'Обращения в работе' },
  { key: 'incidents_open', label: 'Открытые инциденты' },
  { key: 'houses_without_manager', label: 'Дома без УК' },
];

function StatTile({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="card stat-card analytics-tile">
      <div className="stat-card__label">{label}</div>
      <div className="stat-card__value">{number.format(value)}</div>
      {hint && <div className="analytics-tile__hint">{hint}</div>}
    </div>
  );
}

function BarCell({ value, max, label }: { value: number; max: number; label: string }) {
  const width = max > 0 ? Math.max((value / max) * 100, value > 0 ? 3 : 0) : 0;
  return (
    <div className="bar-cell" title={`${label}: ${number.format(value)}`}>
      <span className="bar-cell__value">{number.format(value)}</span>
      <span className="bar-cell__track" aria-hidden="true">
        <span className="bar-cell__bar" style={{ width: `${width}%` }} />
      </span>
    </div>
  );
}

function Breakdown({ rows, onOpen }: { rows: TerritoryBreakdown[]; onOpen: (id: string) => void }) {
  const max = Object.fromEntries(
    COLUMNS.map(({ key }) => [key, Math.max(...rows.map((row) => row.stats[key]), 0)]),
  ) as Record<keyof TerritoryStats, number>;
  return (
    <div className="table-wrap">
      <table className="data-table analytics-table">
        <thead>
          <tr>
            <th>Территория</th>
            {COLUMNS.map((column) => (
              <th key={column.key}>{column.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const territory = row.territory;
            return (
              <tr key={territory?.id ?? 'unassigned'}>
                <td data-label="Территория">
                  {territory ? (
                    <button type="button" className="analytics-table__link" onClick={() => onOpen(territory.id)}>
                      {territory.name}
                    </button>
                  ) : (
                    <span className="cell-muted">Не отнесены к делению</span>
                  )}
                  {territory && (
                    <div className="cell-muted">{TERRITORY_TYPE_LABELS[territory.type as TerritoryType] ?? ''}</div>
                  )}
                </td>
                {COLUMNS.map((column) => (
                  <td key={column.key} data-label={column.label}>
                    <BarCell value={row.stats[column.key]} max={max[column.key]} label={column.label} />
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function AnalyticsPage() {
  const { data: principal } = useMe();
  const territories = useTerritories();
  const [params, setParams] = useSearchParams();
  const roots = useMemo(() => (territories.data ?? []).filter((node) => node.parent_id === null), [territories.data]);
  const territoryId = params.get('territory') ?? roots[0]?.id ?? null;
  const summary = useTerritorySummary(territoryId);

  useEffect(() => {
    if (!params.get('territory') && roots[0]) setParams({ territory: roots[0].id }, { replace: true });
  }, [params, roots, setParams]);

  const open = (id: string) => setParams({ territory: id });
  const data = summary.data;
  const topMax = Math.max(...(data?.top_categories ?? []).map((item) => item.reports), 0);

  if (territories.isSuccess && roots.length === 0) {
    return <EmptyState icon={<HousesIcon />} title="Территории ещё не настроены" />;
  }

  return (
    <AsyncState
      isLoading={territories.isLoading || (summary.isLoading && !data)}
      error={territories.error ?? summary.error}
      onRetry={() => void summary.refetch()}
    >
      {data && (
        <>
          <section className="analytics-header">
            <nav className="analytics-path" aria-label="Путь по территориям">
              {data.path.map((item, index) => (
                <span key={item.id}>
                  {index > 0 && <span className="analytics-path__sep">/</span>}
                  {index < data.path.length - 1 ? (
                    <button type="button" onClick={() => open(item.id)}>
                      {item.name}
                    </button>
                  ) : (
                    <strong>{item.name}</strong>
                  )}
                </span>
              ))}
            </nav>
            {isAdmin(principal) && (
              <select
                className="field analytics-header__picker"
                aria-label="Территория"
                value={territoryId ?? ''}
                onChange={(event) => open(event.target.value)}
              >
                {flattenTerritoryTree(territories.data ?? []).map(({ node, depth }) => (
                  <option key={node.id} value={node.id}>
                    {`${'  '.repeat(depth)}${node.name}`}
                  </option>
                ))}
              </select>
            )}
          </section>

          <div className="stat-grid">
            <StatTile
              label="Дома"
              value={data.total.houses}
              hint={data.total.houses_without_manager ? `без УК: ${number.format(data.total.houses_without_manager)}` : undefined}
            />
            <StatTile label="Жители в приложении" value={data.total.residents} />
            <StatTile
              label="Обращения в работе"
              value={data.total.reports_open}
              hint={`за 30 дней: ${number.format(data.total.reports_last_30_days)}`}
            />
            <StatTile
              label="Открытые инциденты"
              value={data.total.incidents_open}
              hint={
                data.total.incidents_critical_open
                  ? `критических: ${number.format(data.total.incidents_critical_open)}`
                  : `решено: ${number.format(data.total.incidents_resolved)}`
              }
            />
            <StatTile label="УК и ТСЖ" value={data.total.managing_organizations} />
          </div>

          {data.children.length > 0 && (
            <section className="card">
              <div className="card__header">
                <div>
                  <div className="card__title">По делениям</div>
                  <div className="card__meta">Нажмите на название, чтобы открыть его статистику</div>
                </div>
              </div>
              <div className="card__body card__body--flush">
                <Breakdown rows={data.children} onOpen={open} />
              </div>
            </section>
          )}

          {data.top_categories.length > 0 && (
            <section className="card">
              <div className="card__header">
                <div className="card__title">Частые темы обращений</div>
              </div>
              <div className="card__body">
                <ul className="analytics-categories">
                  {data.top_categories.map((item) => (
                    <li key={item.name}>
                      <span className="analytics-categories__name">{item.name}</span>
                      <BarCell value={item.reports} max={topMax} label={item.name} />
                    </li>
                  ))}
                </ul>
              </div>
            </section>
          )}
        </>
      )}
    </AsyncState>
  );
}
