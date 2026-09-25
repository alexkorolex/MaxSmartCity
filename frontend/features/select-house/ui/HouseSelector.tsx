import { Typography } from '@maxhub/max-ui';
import { useMemo } from 'react';

import { useHouse, type House } from '@/entities/geo';
import { AsyncState, CheckCircleIcon, CityIcon, HouseIcon, SearchSelect } from '@/shared/ui';
import type { SearchOption } from '@/shared/ui';

import { useHouseSelection } from '../model/useHouseSelection';

import './HouseSelector.css';

interface HouseSelectorProps {
  value: string | null;
  onChange: (houseId: string | null) => void;
}

function houseTitle(house: House): string {
  return [house.street, house.house_number].filter(Boolean).join(', ') || house.formatted;
}

function cityOptions(cities: string[]): SearchOption[] {
  return cities.map((city) => ({ id: city, label: city }));
}

function houseOptions(houses: House[]): SearchOption[] {
  return houses.map((house) => ({
    id: house.house_id,
    label: houseTitle(house),
    description: house.formatted === houseTitle(house) ? undefined : house.formatted,
    keywords: `${house.street ?? ''} ${house.house_number ?? ''}`,
  }));
}

export function HouseSelector({ value, onChange }: HouseSelectorProps) {
  const selection = useHouseSelection(value);
  const selectedHouse = useHouse(value);
  const cities = useMemo(() => cityOptions(selection.cities), [selection.cities]);
  const houses = useMemo(() => houseOptions(selection.housesInCity), [selection.housesInCity]);
  const city = cities.find((option) => option.id === selection.selectedCity) ?? null;
  // The chosen house need not be among the current search results.
  const house = useMemo(
    () => (selectedHouse.data ? (houseOptions([selectedHouse.data])[0] ?? null) : null),
    [selectedHouse.data],
  );

  const changeCity = (option: SearchOption | null) => {
    if (option?.id === selection.selectedCity) return;
    selection.selectCity(option?.id ?? null);
    onChange(null);
  };

  return (
    <AsyncState isLoading={selection.citiesQuery.isLoading} error={selection.citiesQuery.error} onRetry={() => selection.citiesQuery.refetch()}>
      <section className="house-search-card">
        <SearchSelect label="Город" placeholder="Начните вводить город" options={cities} value={city}
          icon={<CityIcon width={19} height={19} />} emptyMessage="Такой город не найден" onChange={changeCity} />
        <div className="house-search-card__connector" aria-hidden="true" />
        <SearchSelect key={city?.id ?? 'no-city'} label="Адрес дома" placeholder={city ? 'Улица или номер дома' : 'Сначала выберите город'}
          options={houses} value={value ? house : null} icon={<HouseIcon width={19} height={19} />} disabled={!city}
          emptyMessage={selection.isSearching ? 'Ищем…' : 'Дом не найден — проверьте запрос'}
          onQueryChange={selection.setQuery} onChange={(option) => onChange(option?.id ?? null)} />
        {value && house && (
          <div className="house-selection-summary">
            <CheckCircleIcon width={22} height={22} />
            <div><Typography.Text variant="detail-strong" color="primary">Дом выбран</Typography.Text>
              <Typography.Text variant="description" color="secondary">{house.description ?? house.label}</Typography.Text></div>
          </div>
        )}
      </section>
    </AsyncState>
  );
}
