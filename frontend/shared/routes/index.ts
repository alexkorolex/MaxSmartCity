export const ROUTES = {
  home: '/',
  authMax: '/auth/max',
  reportNew: '/report/new',
  myReports: '/reports',
  report: (reportId: string) => `/reports/${reportId}`,
  reportChat: (reportId: string) => `/reports/${reportId}/chat`,
  incident: (incidentId: string) => `/incidents/${incidentId}`,
  incidentResolution: (incidentId: string) => `/incidents/${incidentId}/resolution`,
  myHouse: '/house',
  news: '/news',
  newsItem: (newsId: string) => `/news/${newsId}`,
  notifications: '/notifications',
  profile: '/profile',
  selectHouse: '/profile/house',
  settings: '/settings',
  help: '/help',
} as const;

export { consumeMaxStartRoute, peekMaxStartRoute } from './maxStartRoute';
export { routeFromStartParam, safeNextPath } from './startParam';
