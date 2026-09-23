interface CitySelectProps {
  cities: string[];
  value: string;
  onChange: (city: string) => void;
}

export function CitySelect({ cities, value, onChange }: CitySelectProps) {
  return (
    <div className="filter-bar__field">
      <span className="filter-bar__label">Город</span>
      <select className="field" value={value} onChange={(event) => onChange(event.target.value)}>
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
