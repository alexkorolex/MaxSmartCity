import { useEffect, useState } from 'react';

import { useCities, useHouse, useHouseSearch } from '@/entities/geo';
import { useDebouncedValue } from '@/shared/lib';

/** City + address search for the house picker. Houses are searched on the server (the
 * registry is far too large to load whole); the city of an already chosen house is
 * preselected. */
export function useHouseSelection(initialHouseId?: string | null) {
  const citiesQuery = useCities();
  const initialHouse = useHouse(initialHouseId);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebouncedValue(query);
  const housesQuery = useHouseSearch(selectedCity, debouncedQuery);

  useEffect(() => {
    const city = initialHouse.data?.city;
    if (city && selectedCity === null) setSelectedCity(city);
  }, [initialHouse.data?.city, selectedCity]);

  const selectCity = (city: string | null) => {
    setSelectedCity(city);
    setQuery('');
  };

  return {
    citiesQuery,
    cities: citiesQuery.data ?? [],
    selectedCity,
    selectCity,
    setQuery,
    housesQuery,
    housesInCity: housesQuery.data ?? [],
    isSearching: housesQuery.isFetching || query !== debouncedQuery,
  };
}
