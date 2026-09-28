type Refresher = () => Promise<boolean>;

let refresher: Refresher | null = null;
let inFlight: Promise<boolean> | null = null;

export function registerTokenRefresher(fn: Refresher): void {
  refresher = fn;
}

export function refreshAuthToken(): Promise<boolean> {
  if (!refresher) return Promise.resolve(false);
  inFlight ??= refresher()
    .catch(() => false)
    .finally(() => {
      inFlight = null;
    });
  return inFlight;
}
