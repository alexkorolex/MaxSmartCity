export interface MaxBridgeInitDataUnsafe {
  start_param?: string;
  user?: {
    id: number;
    first_name?: string;
    last_name?: string;
    username?: string;
    /** Profile photo supplied by MAX Bridge for the current mini-app user. */
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
    /** Present only when the page is running as a mini app inside MAX
     * (https://st.max.ru/js/max-web-app.js, loaded unconditionally in index.html). */
    WebApp?: MaxBridgeWebApp;
  }
}
