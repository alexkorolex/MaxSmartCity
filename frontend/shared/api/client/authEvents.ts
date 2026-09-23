type Listener = () => void;

const listeners = new Set<Listener>();

/** Fired by the transport when the server rejects the current token (401). Carries no
 * opinion on what that should mean for the app - a session-owning layer decides that. */
export function emitUnauthorized(): void {
  for (const listener of listeners) listener();
}

export function subscribeUnauthorized(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
