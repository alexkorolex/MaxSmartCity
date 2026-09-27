const UUID = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}';

const START_PARAM_ROUTES: ReadonlyArray<[RegExp, (id: string) => string]> = [
  [new RegExp(`^report_(${UUID})_chat$`), (id) => `/reports/${id}/chat`],
  [new RegExp(`^report_(${UUID})$`), (id) => `/reports/${id}`],
  [new RegExp(`^incident_(${UUID})_resolution$`), (id) => `/incidents/${id}/resolution`],
  [new RegExp(`^incident_(${UUID})$`), (id) => `/incidents/${id}`],
];

export function routeFromStartParam(startParam: string | null | undefined): string | null {
  if (!startParam) return null;
  for (const [pattern, toRoute] of START_PARAM_ROUTES) {
    const match = pattern.exec(startParam);
    if (match) return toRoute(match[1]);
  }
  return null;
}

export function safeNextPath(next: string | null | undefined): string | null {
  if (!next || !next.startsWith('/') || next.startsWith('//') || next.includes('\\')) return null;
  return next;
}
