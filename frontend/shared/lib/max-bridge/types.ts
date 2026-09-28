export interface MaxBridgeInitDataUnsafe {
  start_param?: string;
  user?: {
    id: number;
    first_name?: string;
    last_name?: string;
    username?: string;
    photo_url?: string;
  };
}

export interface MaxBridgeWebApp {
  initData: string;
  initDataUnsafe: MaxBridgeInitDataUnsafe;
  platform: 'ios' | 'android' | 'desktop' | 'web';
  version: string;
}

declare global {
  interface Window {
    WebApp?: MaxBridgeWebApp;
  }
}
