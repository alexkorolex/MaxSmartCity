import { CellHeader, CellList, CellSimple, Radio } from '@maxhub/max-ui';

import { AsyncState, CityIcon, HouseIcon, ListCard } from '@/shared/ui';

import { useHouseSelection } from '../model/useHouseSelection';

interface HouseSelectorProps {
  value: string | null;
  onChange: (houseId: string) => void;
}

export function HouseSelector({ value, onChange }: HouseSelectorProps) {
  const { housesQuery, cities, selectedCity, selectCity, housesInCity } = useHouseSelection(value);

  return (
    <AsyncState isLoading={housesQuery.isLoading} error={housesQuery.error} onRetry={() => housesQuery.refetch()}>
      <>
        <ListCard>
          <CellList mode="full-width" header={<CellHeader>Город</CellHeader>}>
            {cities.map((city) => (
              <CellSimple
                key={city}
                title={city}
                before={<CityIcon width={20} height={20} />}
                after={
                  <Radio
                    name="city"
                    checked={selectedCity === city}
                    onChange={() => selectCity(city)}
                    aria-label={city}
                  />
                }
              />
            ))}
          </CellList>
        </ListCard>

        {selectedCity && (
          <ListCard>
            <CellList mode="full-width" header={<CellHeader>Дом</CellHeader>}>
              {housesInCity.map((house) => (
                <CellSimple
                  key={house.house_id}
                  title={[house.street, house.house_number].filter(Boolean).join(', ') || house.formatted}
                  subtitle={house.formatted}
                  subtitleMode="tertiary"
                  before={<HouseIcon width={20} height={20} />}
                  after={
                    <Radio
                      name="house"
                      checked={value === house.house_id}
                      onChange={() => onChange(house.house_id)}
                      aria-label={house.formatted}
                    />
                  }
                />
              ))}
            </CellList>
          </ListCard>
        )}
      </>
    </AsyncState>
  );
}
