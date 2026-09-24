interface DateFormatOptions {
  year?: boolean;
  fallback?: string;
}

function toValidDate(value: string | null): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatCalendarDate(value: string | null, options: DateFormatOptions = {}): string {
  const date = toValidDate(value);
  if (!date) return options.fallback ?? '';

  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'long',
    year: options.year ? 'numeric' : undefined,
  });
}

export function formatDateTime(value: string | null): string {
  const date = toValidDate(value);
  if (!date) return '';

  return date.toLocaleString('ru-RU', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}
