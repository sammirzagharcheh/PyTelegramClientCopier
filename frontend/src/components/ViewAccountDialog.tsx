import { Smartphone, X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../lib/api';
import { formatLocalDateTime } from '../lib/formatDateTime';
import { AccountTypeBadge } from './AccountTypeBadge';
import { AccountStatusBadge } from './AccountStatusBadge';

type AccountDetail = {
  id: number;
  user_id: number;
  name: string | null;
  type: string;
  session_path: string | null;
  phone: string | null;
  status: string;
  created_at: string | null;
};

type Props = {
  accountId: number;
  onClose: () => void;
};

export function ViewAccountDialog({ accountId, onClose }: Props) {
  const { data: account, isLoading } = useQuery({
    queryKey: ['account', accountId],
    queryFn: async () => (await api.get<AccountDetail>(`/accounts/${accountId}`)).data,
    enabled: !!accountId,
  });

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Smartphone className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <h2 className="text-xl font-bold">Account Details</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-md text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {isLoading ? (
          <div className="animate-pulse h-24 bg-gray-200 dark:bg-gray-700 rounded" />
        ) : account ? (
          <dl className="space-y-4">
            <div>
              <dt className="text-sm text-gray-500 dark:text-gray-400">Name</dt>
              <dd className="text-sm font-medium">{account.name || '—'}</dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500 dark:text-gray-400">Type</dt>
              <dd>
                <AccountTypeBadge type={account.type} />
              </dd>
            </div>
            <div>
              <dt className="text-sm text-gray-500 dark:text-gray-400">Status</dt>
              <dd>
                <AccountStatusBadge status={account.status} />
              </dd>
            </div>
            {account.phone && (
              <div>
                <dt className="text-sm text-gray-500 dark:text-gray-400">Phone</dt>
                <dd className="text-sm font-mono">{account.phone}</dd>
              </div>
            )}
            <div>
              <dt className="text-sm text-gray-500 dark:text-gray-400">Created</dt>
              <dd className="text-sm" title={account.created_at ?? undefined}>
                {formatLocalDateTime(account.created_at)}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-gray-500">Account not found.</p>
        )}
        <div className="mt-6 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
