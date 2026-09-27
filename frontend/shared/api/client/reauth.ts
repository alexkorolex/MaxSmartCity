type Reauthenticate = () => Promise<boolean>;

let reauthenticate: Reauthenticate | null = null;

export function setReauthenticateHandler(handler: Reauthenticate | null): void {
  reauthenticate = handler;
}

export function tryReauthenticate(): Promise<boolean> {
  return reauthenticate ? reauthenticate() : Promise.resolve(false);
}
