export interface SearchableOption {
  id: string;
  label: string;
  description?: string;
  keywords?: string;
}

function normalize(value: string): string {
  return value.trim().toLocaleLowerCase('ru-RU').replace(/\s+/g, ' ');
}

export function filterSearchOptions<T extends SearchableOption>(options: T[], query: string): T[] {
  const normalized = normalize(query);
  if (!normalized) return options;

  return options.filter((option) => {
    const searchable = `${option.label} ${option.description ?? ''} ${option.keywords ?? ''}`;
    return normalize(searchable).includes(normalized);
  });
}
