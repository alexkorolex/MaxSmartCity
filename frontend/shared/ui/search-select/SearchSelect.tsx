import { Input } from '@maxhub/max-ui';
import { useEffect, useId, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

import { filterSearchOptions } from '@/shared/lib';
import type { SearchableOption } from '@/shared/lib';
import { CheckCircleIcon, SearchIcon } from '@/shared/ui/icons';

import './SearchSelect.css';

export type SearchOption = SearchableOption;

interface SearchSelectProps {
  label: string;
  placeholder: string;
  options: SearchOption[];
  value: SearchOption | null;
  icon: ReactNode;
  emptyMessage: string;
  disabled?: boolean;
  onChange: (option: SearchOption | null) => void;
  /** Server-side search: the typed text is reported here and `options` are shown as
   * given (already filtered by the server) instead of being filtered locally. */
  onQueryChange?: (query: string) => void;
}

interface OptionsListProps {
  options: SearchOption[];
  selectedId?: string;
  emptyMessage: string;
  onSelect: (option: SearchOption) => void;
}

function OptionsList({ options, selectedId, emptyMessage, onSelect }: OptionsListProps) {
  if (options.length === 0) return <div className="search-select__empty">{emptyMessage}</div>;
  return (
    <div className="search-select__options">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          role="option"
          aria-selected={selectedId === option.id}
          className="search-select__option"
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => onSelect(option)}
        >
          <span className="search-select__option-copy">
            <strong>{option.label}</strong>
            {option.description && <small>{option.description}</small>}
          </span>
          {selectedId === option.id && <CheckCircleIcon width={20} height={20} />}
        </button>
      ))}
    </div>
  );
}

function useSearchSelect(options: SearchOption[], value: SearchOption | null, disabled: boolean | undefined,
  onChange: SearchSelectProps['onChange'], onQueryChange: SearchSelectProps['onQueryChange']) {
  const [query, setQuery] = useState(value?.label ?? '');
  const [isOpen, setIsOpen] = useState(false);
  const visibleOptions = useMemo(
    () => (onQueryChange ? options : filterSearchOptions(options, query)).slice(0, 30),
    [options, query, onQueryChange],
  );

  useEffect(() => {
    if (value) setQuery(value.label);
    if (disabled) setQuery('');
  }, [disabled, value]);

  function selectOption(option: SearchOption): void {
    setQuery(option.label);
    setIsOpen(false);
    onChange(option);
  }

  function changeQuery(nextQuery: string): void {
    setQuery(nextQuery);
    setIsOpen(true);
    onQueryChange?.(nextQuery);
    if (value) onChange(null);
  }

  return { query, isOpen, visibleOptions, setIsOpen, selectOption, changeQuery };
}

export function SearchSelect(props: SearchSelectProps) {
  const { label, placeholder, options, value, icon, emptyMessage, disabled, onChange, onQueryChange } = props;
  const inputId = useId();
  const listId = useId();
  const state = useSearchSelect(options, value, disabled, onChange, onQueryChange);

  return (
    <div className={`search-select${disabled ? ' search-select--disabled' : ''}`}>
      <label className="search-select__label" htmlFor={inputId}>
        <span className="search-select__label-icon">{icon}</span>{label}
      </label>
      <div className="search-select__input">
        <Input
          id={inputId}
          value={state.query}
          placeholder={placeholder}
          iconBefore={<SearchIcon width={19} height={19} />}
          withClearButton
          disabled={disabled}
          role="combobox"
          aria-expanded={state.isOpen}
          aria-controls={listId}
          aria-autocomplete="list"
          onFocus={(event) => { state.setIsOpen(true); if (value) event.currentTarget.select(); }}
          onBlur={() => state.setIsOpen(false)}
          onKeyDown={(event) => { if (event.key === 'Escape') state.setIsOpen(false); }}
          onChange={(event) => state.changeQuery(event.target.value)}
        />
      </div>
      {state.isOpen && (
        <div id={listId} className="search-select__popover" role="listbox">
          <OptionsList options={state.visibleOptions} selectedId={value?.id} emptyMessage={emptyMessage}
            onSelect={state.selectOption} />
        </div>
      )}
    </div>
  );
}
