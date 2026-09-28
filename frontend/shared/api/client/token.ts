const STORAGE_KEY = 'maxsc.resident.token';

let cachedToken: string | null | undefined;

export function getAuthToken(): string | null {
  if (cachedToken !== undefined) return cachedToken;
  try {
    cachedToken = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    cachedToken = null;
  }
  return cachedToken;
}

export function setAuthToken(token: string): void {
  cachedToken = token;
  try {
    window.localStorage.setItem(STORAGE_KEY, token);
  } catch {}
}

export function clearAuthToken(): void {
  cachedToken = null;
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {}
}
