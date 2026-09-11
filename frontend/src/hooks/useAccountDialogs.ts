import { useQuery } from '@tanstack/react-query';
import { api, type TelegramDialog } from '../lib/api';

type DialogListResponse = {
  items: TelegramDialog[];
};

export function useAccountDialogs(accountId: number | null) {
  return useQuery({
    queryKey: ['accounts', accountId, 'dialogs'],
    queryFn: async () =>
      (await api.get<DialogListResponse>(`/accounts/${accountId}/dialogs`)).data.items,
    enabled: accountId != null,
    staleTime: 60 * 1000,
    retry: (failureCount, error) => {
      const status =
        error &&
        typeof error === 'object' &&
        'response' in error &&
        error.response &&
        typeof error.response === 'object' &&
        'status' in error.response
          ? (error.response as { status: number }).status
          : 0;
      if (status === 409 || status === 400) return false;
      return failureCount < 2;
    },
  });
}
