import { useState, type FormEvent } from 'react';

import {
  CHILD_TERRITORY_TYPES,
  flattenTerritoryTree,
  TERRITORY_TYPE_LABELS,
  useCreateTerritory,
  useDeleteTerritory,
  useUpdateTerritory,
  type TerritoryNode,
  type TerritoryType,
} from '@/entities/territory';
import { apiErrorMessage } from '@/shared/lib';

import './ManageTerritories.css';

interface TerritoryTreeProps {
  nodes: TerritoryNode[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  canAddCity: boolean;
}

function formatHouses(count: number): string {
  return new Intl.NumberFormat('ru-RU').format(count);
}

export function TerritoryTree({ nodes, selectedId, onSelect, canAddCity }: TerritoryTreeProps) {
  const items = flattenTerritoryTree(nodes);
  const create = useCreateTerritory();
  const [cityName, setCityName] = useState('');

  function addCity(event: FormEvent) {
    event.preventDefault();
    if (!cityName.trim()) return;
    create.mutate({ name: cityName.trim(), type: 'CITY' }, { onSuccess: () => setCityName('') });
  }

  return (
    <div className="territory-tree">
      {items.length === 0 ? (
        <p className="territory-tree__empty">Территорий пока нет — начните с города.</p>
      ) : (
        <ul className="territory-tree__list" role="tree" aria-label="Территориальное деление">
          {items.map(({ node, depth }) => (
            <li key={node.id} role="treeitem" aria-selected={node.id === selectedId} aria-level={depth + 1}>
              <button
                type="button"
                className={`territory-tree__row${node.id === selectedId ? ' territory-tree__row--selected' : ''}`}
                style={{ paddingInlineStart: `${12 + depth * 18}px` }}
                onClick={() => onSelect(node.id)}
              >
                <span className="territory-tree__name">{node.name}</span>
                <span className="territory-tree__type">{TERRITORY_TYPE_LABELS[node.type]}</span>
                <span className="territory-tree__count" title="Домов">
                  {formatHouses(node.house_count)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {canAddCity && (
        <form className="territory-tree__add" onSubmit={addCity}>
          <label className="sr-only" htmlFor="territory-city">
            Новый город
          </label>
          <input
            id="territory-city"
            className="field"
            placeholder="Новый город, как в адресах домов"
            value={cityName}
            onChange={(event) => setCityName(event.target.value)}
          />
          <button type="submit" className="btn btn--ghost" disabled={!cityName.trim() || create.isPending}>
            Добавить город
          </button>
          {create.isError && <div className="form-error">{apiErrorMessage(create.error)}</div>}
        </form>
      )}
    </div>
  );
}

interface TerritoryEditorProps {
  node: TerritoryNode;
  onDeleted: (parentId: string | null) => void;
  onCreated: (name: string) => void;
}

export function TerritoryEditor({ node, onDeleted, onCreated }: TerritoryEditorProps) {
  const create = useCreateTerritory();
  const update = useUpdateTerritory();
  const remove = useDeleteTerritory();
  const [childName, setChildName] = useState('');
  const [childType, setChildType] = useState<TerritoryType>('DISTRICT');
  const [name, setName] = useState(node.name);
  const isRoot = node.parent_id === null;

  function addChild(event: FormEvent) {
    event.preventDefault();
    const trimmed = childName.trim();
    if (!trimmed) return;
    create.mutate(
      { name: trimmed, type: childType, parent_id: node.id },
      {
        onSuccess: () => {
          setChildName('');
          onCreated(trimmed);
        },
      },
    );
  }

  function rename(event: FormEvent) {
    event.preventDefault();
    if (name.trim() && name.trim() !== node.name) update.mutate({ id: node.id, payload: { name: name.trim() } });
  }

  const error = create.error ?? update.error ?? remove.error;

  return (
    <div className="territory-editor">
      <form className="territory-editor__row" onSubmit={addChild}>
        <div className="territory-editor__grow">
          <label className="field-label" htmlFor="territory-child-name">
            Вложенное деление
          </label>
          <input
            id="territory-child-name"
            className="field"
            placeholder="Например, Бежицкий район"
            value={childName}
            onChange={(event) => setChildName(event.target.value)}
          />
        </div>
        <div>
          <label className="field-label" htmlFor="territory-child-type">
            Тип
          </label>
          <select
            id="territory-child-type"
            className="field"
            value={childType}
            onChange={(event) => setChildType(event.target.value as TerritoryType)}
          >
            {CHILD_TERRITORY_TYPES.map((type) => (
              <option key={type} value={type}>
                {TERRITORY_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" className="btn" disabled={!childName.trim() || create.isPending}>
          Добавить
        </button>
      </form>
      {!isRoot && (
        <form className="territory-editor__row" onSubmit={rename}>
          <div className="territory-editor__grow">
            <label className="field-label" htmlFor="territory-name">
              Название
            </label>
            <input id="territory-name" className="field" value={name} onChange={(event) => setName(event.target.value)} />
          </div>
          <button
            type="submit"
            className="btn btn--ghost"
            disabled={!name.trim() || name.trim() === node.name || update.isPending}
          >
            Переименовать
          </button>
          <button
            type="button"
            className="btn btn--danger-ghost"
            disabled={remove.isPending}
            onClick={() => {
              if (window.confirm(`Удалить «${node.name}»? Его дома вернутся на уровень выше.`)) {
                remove.mutate(node.id, { onSuccess: () => onDeleted(node.parent_id) });
              }
            }}
          >
            Удалить
          </button>
        </form>
      )}
      {error && <div className="form-error">{apiErrorMessage(error)}</div>}
    </div>
  );
}
