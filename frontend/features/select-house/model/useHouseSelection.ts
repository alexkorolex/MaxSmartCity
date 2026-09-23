import { useEffect, useMemo, useState } from 'react';

import { useHouses } from '@/entities/geo';

export function useHouseSelection(initialHouseId?: string | null) {
  const housesQuery = useHouses();
  const houses = useMemo(() => housesQuery.data ?? [], [housesQuery.data]);

  const initialCity = useMemo(
    () => houses.find((house) => house.house_id === initialHouseId)?.city ?? null,
    [houses, initialHouseId],
  );

  const [selectedCity, setSelectedCity] = useState<string | null>(null);

  useEffect(() => {
    if (initialCity && selectedCity === null) setSelectedCity(initialCity);
  }, [initialCity, selectedCity]);

  const cities = useMemo(() => {
    const unique = new Set(houses.map((house) => house.city).filter((city): city is string => Boolean(city)));
    return Array.from(unique).sort((a, b) => a.localeCompare(b, 'ru'));
  }, [houses]);

  const housesInCity = useMemo(
    () => houses.filter((house) => house.city === selectedCity),
    [houses, selectedCity],
  );

  const selectCity = (city: string | null) => {
    setSelectedCity(city);
  };

  return {
    housesQuery,
    cities,
    selectedCity,
    selectCity,
    housesInCity,
  };
}
