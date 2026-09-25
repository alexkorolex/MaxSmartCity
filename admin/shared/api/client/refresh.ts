type Refresher = () => Promise<boolean>;

let refresher: Refresher | null = null;
let inFlight: Promise<boolean> | null = null;

/** The session layer plugs in how to renew the access token (it owns the auth endpoints);
 * the transport only knows *when* to ask - on a 401. */
export function registerTokenRefresher(fn: Refresher): void {
  refresher = fn;
}

/** Renew the access token once for everyone: several requests failing with 401 at the
 * same moment share a single refresh call instead of racing each other. */
export function refreshAuthToken(): Promise<boolean> {
  if (!refresher) return Promise.resolve(false);
  inFlight ??= refresher()
    .catch(() => false)
    .finally(() => {
      inFlight = null;
    });
  return inFlight;
}
