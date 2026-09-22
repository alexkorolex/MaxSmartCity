import '@maxhub/max-ui/dist/styles.css';

import { AppProviders } from './providers';
import { AppRouter } from './router';
import './styles/index.css';

export function App() {
  return (
    <AppProviders>
      <AppRouter />
    </AppProviders>
  );
}
