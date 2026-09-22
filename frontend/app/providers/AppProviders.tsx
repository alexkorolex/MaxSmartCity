import { MaxUI } from '@maxhub/max-ui';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { PropsWithChildren } from 'react';
import { useState } from 'react';
import { BrowserRouter } from 'react-router-dom';

import { useTheme } from '@/features/change-theme';

export function AppProviders({ children }: PropsWithChildren) {
  const { resolvedTheme } = useTheme();
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <MaxUI resetBody colorScheme={resolvedTheme}>
        <BrowserRouter>{children}</BrowserRouter>
      </MaxUI>
    </QueryClientProvider>
  );
}
