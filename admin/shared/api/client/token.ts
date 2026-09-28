const STORAGE_KEY = 'maxsc-admin.token';
const LEGACY_REFRESH_STORAGE_KEY = 'maxsc-admin.refresh-token';

let cachedToken: string | null | undefined;

function read(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {}
}

export function getAuthToken(): string | null {
  if (cachedToken !== undefined) return cachedToken;
  cachedToken = read(STORAGE_KEY);
  return cachedToken;
}

export function setAuthToken(token: string): void {
  cachedToken = token;
  write(STORAGE_KEY, token);
}

export function clearAuthToken(): void {
  cachedToken = null;
  write(STORAGE_KEY, null);
}

write(LEGACY_REFRESH_STORAGE_KEY, null);
