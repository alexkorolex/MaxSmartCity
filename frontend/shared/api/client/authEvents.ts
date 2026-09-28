type Listener = () => void;

const listeners = new Set<Listener>();

export function emitUnauthorized(): void {
  for (const listener of listeners) listener();
}

export function subscribeUnauthorized(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
