/** `+79621403018` -> `+7 (962) 140-30-18`; anything that isn't a Russian mobile/city
 * number in E.164 is shown as-is. */
export function formatPhone(phone: string): string {
  const match = /^\+7(\d{3})(\d{3})(\d{2})(\d{2})$/.exec(phone);
  if (!match) return phone;
  const [, code, first, second, third] = match;
  return `+7 (${code}) ${first}-${second}-${third}`;
}

/** `https://www.domplus.ru/about` -> `domplus.ru` - short enough for a list row. */
export function websiteLabel(website: string): string {
  try {
    return new URL(website).hostname.replace(/^www\./, '');
  } catch {
    return website;
  }
}
