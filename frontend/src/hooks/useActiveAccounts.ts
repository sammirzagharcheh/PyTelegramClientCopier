import { useQuery } from '@tanstack/react-query';
import { api, type TelegramAccount } from '../lib/api';

type PaginatedAccounts = {
  items: TelegramAccount[];
  total: number;
};

export function isUsableActiveAccount(account: TelegramAccount): boolean {
  if (account.status !== 'active') return false;
  if (account.type === 'user') return Boolean(account.session_path);
  if (account.type === 'bot') return true;
  return false;
}

export function formatAccountLabel(account: TelegramAccount): string {
  return account.name?.trim() || account.phone?.trim() || `Account #${account.id}`;
}

export function useActiveAccounts() {
  return useQuery({
    queryKey: ['accounts', 'active'],
    queryFn: async () =>
      (await api.get<PaginatedAccounts>('/accounts?status=active&page=1&page_size=100')).data,
    staleTime: 5 * 60 * 1000,
    select: (data) => data.items.filter(isUsableActiveAccount),
  });
}
