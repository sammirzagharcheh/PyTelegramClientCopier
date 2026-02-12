import { Inbox, Plus, Smartphone, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { AddAccountDialog } from '../../components/AddAccountDialog';
import { PageHeader } from '../../components/PageHeader';
import { SortableTh } from '../../components/SortableTh';
import { StatusBadge } from '../../components/StatusBadge';
import { Pagination } from '../../components/Pagination';

type Account = {
  id: number;
  user_id: number;
  name: string | null;
  type: string;
  status: string;
  created_at: string | null;
};

type PaginatedAccounts = { items: Account[]; total: number; page: number; page_size: number; total_pages: number };

export function Accounts() {
  const [showAdd, setShowAdd] = useState(false);
  const [accountToDelete, setAccountToDelete] = useState<Account | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState<string>('id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['accounts', page, pageSize, sortBy, sortOrder],
    queryFn: async () =>
      (await api.get<PaginatedAccounts>(`/accounts?page=${page}&page_size=${pageSize}&sort_by=${sortBy}&sort_order=${sortOrder}`)).data,
  });
  const accounts = data?.items ?? [];

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
      <PageHeader
        title="Telegram Accounts"
        icon={Smartphone}
        subtitle="Manage your connected Telegram accounts"
        actions={
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-2 px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" />
            Add Account
          </button>
        }
      />
      {showAdd && <AddAccountDialog onClose={() => setShowAdd(false)} />}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <SortableTh label="ID" sortKey="id" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Name" sortKey="name" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Type" sortKey="type" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Status" sortKey="status" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {accounts.map((acc) => (
              <tr key={acc.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-6 py-4 text-sm">{acc.id}</td>
                <td className="px-6 py-4 text-sm">{acc.name || '—'}</td>
                <td className="px-6 py-4 text-sm">
                  <StatusBadge status={acc.type} variant="type" />
                </td>
                <td className="px-6 py-4 text-sm">
                  <StatusBadge status={acc.status} variant="status" />
                </td>
              <td className="px-6 py-4 text-sm text-right">
                <button
                  type="button"
                  onClick={() => handleDelete(acc)}
                  className="flex items-center gap-1 px-3 py-1 rounded border border-red-500 text-red-600 text-xs hover:bg-red-50 dark:hover:bg-red-900/20"
                  disabled={deleteMutation.isPending && accountToDelete?.id === acc.id}
                >
                  <Trash2 className="h-3 w-3" />
                  Delete
                </button>
              </td>
              </tr>
            ))}
          </tbody>
        </table>
        {accounts.length === 0 && (
          <div className="p-8 text-center text-gray-500 flex flex-col items-center gap-2">
            <Inbox className="h-12 w-12 text-gray-400" />
            <p>No accounts yet. Add one from the mappings flow.</p>
          </div>
        )}
        {data && (
          <Pagination
            page={data.page}
            pageSize={data.page_size}
            total={data.total}
            totalPages={data.total_pages}
            onPageChange={setPage}
            onPageSizeChange={(n) => { setPageSize(n); setPage(1); }}
          />
        )}
      </div>

      {accountToDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setAccountToDelete(null)}>
          <div
            className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-4">
              <Trash2 className="h-5 w-5 text-red-600" />
              <h2 className="text-xl font-bold">Delete Telegram Account</h2>
            </div>
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
