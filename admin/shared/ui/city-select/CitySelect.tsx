interface CitySelectProps {
  cities: string[];
  value: string;
  onChange: (city: string) => void;
}

export function CitySelect({ cities, value, onChange }: CitySelectProps) {
  const selectId = useId();

  return (
    <div className="filter-bar__field">
      <label className="filter-bar__label" htmlFor={selectId}>Город</label>
      <select id={selectId} className="field" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Все города</option>
        {cities.map((city) => (
          <option key={city} value={city}>
            {city}
          </option>
        ))}
      </select>
    </div>
  );
}
import { useId } from 'react';
