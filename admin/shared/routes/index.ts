export const ROUTES = {
  login: '/login',
  home: '/',
  organizations: '/organizations',
  staff: '/staff',
  residents: '/residents',
  resident: (residentId: string) => `/residents/${residentId}`,
  incidents: '/incidents',
  incident: (incidentId: string) => `/incidents/${incidentId}`,
  news: '/news',
} as const;
