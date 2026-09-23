import { QueryClient } from '@tanstack/react-query';

// A module-level singleton (rather than one created inside a component) so code outside
// the React tree - the token store's login/logout handlers - can clear it directly and
// synchronously, with no render-timing race against components mounting/unmounting.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
  },
});
