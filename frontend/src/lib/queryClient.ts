/**
 * React Query client configuration (staleTime, gcTime, etc.).
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClientDefaultOptions = {
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      gcTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
} as const;

export function createQueryClient() {
  return new QueryClient(queryClientDefaultOptions);
}

/** Invalidate dashboard setup checklist + stats after account/mapping/worker changes. */
export function invalidateDashboardStats(queryClient: QueryClient) {
  void queryClient.invalidateQueries({ queryKey: ['stats', 'dashboard'] });
  void queryClient.invalidateQueries({ queryKey: ['admin', 'stats', 'dashboard'] });
}
