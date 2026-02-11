import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { AddAccountDialog } from '../../components/AddAccountDialog';

type Account = {
  id: number;
  user_id: number;
  name: string | null;
  type: string;
  status: string;
  created_at: string | null;
};

export function Accounts() {
  const [showAdd, setShowAdd] = useState(false);
  const [accountToDelete, setAccountToDelete] = useState<Account | null>(null);
  const queryClient = useQueryClient();
  const { data: accounts, isLoading } = useQuery({
    queryKey: ['accounts'],
    queryFn: async () => (await api.get<Account[]>('/accounts')).data,
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/accounts/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts'] });
      setAccountToDelete(null);
    },
  });

  const handleDelete = (acc: Account) => {
    setAccountToDelete(acc);
  };

  const confirmDelete = () => {
    if (!accountToDelete) return;
    deleteMutation.mutate(accountToDelete.id);
  };

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Telegram Accounts</h1>
        <button onClick={() => setShowAdd(true)} className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">
          Add Account
        </button>
      </div>
      {showAdd && <AddAccountDialog onClose={() => setShowAdd(false)} />}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Status</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {(accounts ?? []).map((acc) => (
              <tr key={acc.id}>
                <td className="px-6 py-4 text-sm">{acc.id}</td>
                <td className="px-6 py-4 text-sm">{acc.name || '—'}</td>
                <td className="px-6 py-4 text-sm">{acc.type}</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2 py-1 rounded text-xs ${acc.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                    {acc.status}
                  </span>
                </td>
              <td className="px-6 py-4 text-sm text-right">
                <button
                  type="button"
                  onClick={() => handleDelete(acc)}
                  className="px-3 py-1 rounded border border-red-500 text-red-600 text-xs hover:bg-red-50 dark:hover:bg-red-900/20"
                  disabled={deleteMutation.isPending && accountToDelete?.id === acc.id}
                >
                  Delete
                </button>
              </td>
              </tr>
            ))}
          </tbody>
        </table>
        {(accounts ?? []).length === 0 && (
          <div className="p-8 text-center text-gray-500">No accounts yet. Add one from the mappings flow.</div>
        )}
      </div>

      {accountToDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setAccountToDelete(null)}>
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-xl font-bold mb-4">Delete Telegram Account</h2>
            <p className="text-sm text-gray-600 dark:text-gray-300 mb-4">
              Are you sure you want to delete the account <span className="font-semibold">{accountToDelete.name || accountToDelete.id}</span>?
              This will remove this Telegram account from the copier, delete its session file, disable any mappings that use it,
              and stop any running workers for this account. Existing message logs are kept.
            </p>
            {deleteMutation.isError && (
              <p className="mb-3 text-sm text-red-600">
                Failed to delete account. {(deleteMutation.error as any)?.response?.data?.detail ?? 'Please try again.'}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setAccountToDelete(null)}
                className="px-4 py-2 rounded border border-gray-300"
                disabled={deleteMutation.isPending}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                disabled={deleteMutation.isPending}
                className="px-4 py-2 rounded bg-red-600 text-white disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deleting…' : 'Delete account'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
