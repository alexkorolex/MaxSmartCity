/** `+79621403018` -> `+7 (962) 140-30-18`; anything else is shown as-is. */
export function formatPhone(phone: string): string {
  const match = /^\+7(\d{3})(\d{3})(\d{2})(\d{2})$/.exec(phone);
  if (!match) return phone;
  const [, code, first, second, third] = match;
  return `+7 (${code}) ${first}-${second}-${third}`;
}
