const STORAGE_KEY = 'maxsc-admin.token';
const REFRESH_STORAGE_KEY = 'maxsc-admin.refresh-token';

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
  } catch {
    /* private mode / storage disabled - session stays in-memory for this tab */
  }
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

/** Long-lived (24 h) token that buys new short-lived access tokens, see `refresh.ts`. Read
 * from storage every time, so a refresh done in another tab is picked up here too. */
export function getRefreshToken(): string | null {
  return read(REFRESH_STORAGE_KEY);
}

export function setRefreshToken(token: string | null): void {
  write(REFRESH_STORAGE_KEY, token);
}

export function clearAuthToken(): void {
  cachedToken = null;
  write(STORAGE_KEY, null);
  write(REFRESH_STORAGE_KEY, null);
}
