import { useId, useState } from 'react';

import { useCities, useHouseSearch } from '../model/queries';
import type { House } from '../model/types';

import './HouseSearchField.css';

interface HouseSearchFieldProps {
  value: House | null;
  onChange: (house: House | null) => void;
  isDisabled?: (house: House) => boolean;
  describe?: (house: House) => string;
}

function defaultDescription(house: House): string {
  return house.managed_by_organization_name ? `Обслуживает: ${house.managed_by_organization_name}` : 'Свободен';
}

export function HouseSearchField({ value, onChange, isDisabled, describe = defaultDescription }: HouseSearchFieldProps) {
  const idPrefix = useId();
  const { data: cities } = useCities();
  const [query, setQuery] = useState('');
  const [city, setCity] = useState('');
  const search = useHouseSearch(query, city);
  const resultsId = `${idPrefix}-results`;
  const isSearchOpen = !value && query.trim().length >= 2;

  return (
    <div className="house-search">
      <div className="form-grid">
        <div>
          <label className="field-label" htmlFor={`${idPrefix}-city`}>
            Город
          </label>
          <select
            id={`${idPrefix}-city`}
            className="field"
            value={city}
            onChange={(event) => {
              setCity(event.target.value);
              onChange(null);
            }}
          >
            <option value="">Все города</option>
            {(cities ?? []).map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="field-label" htmlFor={`${idPrefix}-query`}>
            Адрес
          </label>
          <input
            id={`${idPrefix}-query`}
            className="field"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={isSearchOpen}
            aria-controls={resultsId}
            placeholder="Улица и номер дома"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              onChange(null);
            }}
          />
        </div>
      </div>

      {value ? (
        <div className="house-search__selected">
          <div>
            <div className="house-search__address">{value.formatted}</div>
            <div className="house-search__manager">{describe(value)}</div>
          </div>
          <button type="button" className="btn btn--ghost btn--small" onClick={() => onChange(null)}>
            Другой дом
          </button>
        </div>
      ) : (
        isSearchOpen && (
          <div id={resultsId} className="house-search__results" role="listbox" aria-label="Найденные дома">
            {search.isLoading && <div className="house-search__hint">Ищем…</div>}
            {search.data?.length === 0 && <div className="house-search__hint">Ничего не найдено</div>}
            {search.data?.map((candidate) => (
              <button
                key={candidate.house_id}
                type="button"
                role="option"
                aria-selected={false}
                className="house-search__option"
                disabled={isDisabled?.(candidate) ?? false}
                onClick={() => onChange(candidate)}
              >
                <span className="house-search__address">{candidate.formatted}</span>
                <span className="house-search__manager">{describe(candidate)}</span>
              </button>
            ))}
          </div>
        )
      )}
    </div>
  );
}
