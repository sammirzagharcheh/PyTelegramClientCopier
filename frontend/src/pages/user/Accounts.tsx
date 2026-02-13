import { Inbox, Plus, Smartphone, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { AddAccountDialog } from '../../components/AddAccountDialog';
import { EditAccountDialog } from '../../components/EditAccountDialog';
import { ViewAccountDialog } from '../../components/ViewAccountDialog';
import { AccountTypeBadge } from '../../components/AccountTypeBadge';
import { AccountStatusBadge } from '../../components/AccountStatusBadge';
import { AccountTableActions } from '../../components/AccountTableActions';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { useToast } from '../../components/Toast';
import { PageHeader } from '../../components/PageHeader';
import { SortableTh } from '../../components/SortableTh';
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
  const [editingAccount, setEditingAccount] = useState<Account | null>(null);
  const [viewingAccountId, setViewingAccountId] = useState<number | null>(null);
  const [accountToDelete, setAccountToDelete] = useState<Account | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState<string>('id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();

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
      showToast('Account deleted');
    },
  });

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
      {editingAccount && (
        <EditAccountDialog account={editingAccount} onClose={() => setEditingAccount(null)} />
      )}
      {viewingAccountId && (
        <ViewAccountDialog accountId={viewingAccountId} onClose={() => setViewingAccountId(null)} />
      )}
      {accountToDelete && (
        <ConfirmDialog
          title="Delete Telegram Account"
          message={
            <>
              Are you sure you want to delete the account{' '}
              <span className="font-semibold">{accountToDelete.name || accountToDelete.id}</span>? This
              will remove this Telegram account from the copier, delete its session file, disable any
              mappings that use it, and stop any running workers for this account. Existing message
              logs are kept.
              {deleteMutation.isError && (
                <p className="mt-3 text-sm text-red-600">
                  Failed to delete account.{' '}
                  {(deleteMutation.error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
                    'Please try again.'}
                </p>
              )}
            </>
          }
          confirmLabel="Delete account"
          variant="danger"
          icon={<Trash2 className="h-5 w-5 text-red-600" />}
          onConfirm={() => deleteMutation.mutate(accountToDelete.id)}
          onCancel={() => setAccountToDelete(null)}
          isPending={deleteMutation.isPending}
        />
      )}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <SortableTh label="ID" sortKey="id" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Name" sortKey="name" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Type" sortKey="type" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Status" sortKey="status" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase w-32 min-w-[120px]">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {accounts.map((acc) => (
              <tr key={acc.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-6 py-4 text-sm">{acc.id}</td>
                <td className="px-6 py-4 text-sm">{acc.name || '—'}</td>
                <td className="px-6 py-4 text-sm">
                  <AccountTypeBadge type={acc.type} />
                </td>
                <td className="px-6 py-4 text-sm">
                  <AccountStatusBadge status={acc.status} />
                </td>
                <td className="px-6 py-4 text-sm text-right">
                  <AccountTableActions
                    onEdit={() => setEditingAccount(acc)}
                    onView={() => setViewingAccountId(acc.id)}
                    onDelete={() => setAccountToDelete(acc)}
                  />
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
    </div>
  );
}
