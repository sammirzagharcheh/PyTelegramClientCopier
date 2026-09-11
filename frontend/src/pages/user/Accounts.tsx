import { Plus, Smartphone, Trash2 } from 'lucide-react';
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
import { TableSkeleton } from '../../components/Skeleton';
import { Button } from '../../components/ui/Button';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { TableShell, Tbody, Td, Th, Thead, Tr } from '../../components/ui/TableShell';
import { errorMessage } from '../../lib/apiError';

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

  const { data, isLoading, isError, error, refetch } = useQuery({
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
      showToast('Account deleted', 'success');
    },
  });

  const handleSort = (key: string, order: 'asc' | 'desc') => {
    setSortBy(key);
    setSortOrder(order);
    setPage(1);
  };

  const sortProps = { currentSort: sortBy, currentOrder: sortOrder, onSort: handleSort };

  return (
    <div>
      <PageHeader
        title="Telegram Accounts"
        icon={Smartphone}
        subtitle="Manage your connected Telegram accounts"
        actions={
          <Button icon={Plus} onClick={() => setShowAdd(true)}>
            Add Account
          </Button>
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
              Deleting{' '}
              <span className="font-medium text-ink">
                {accountToDelete.name || accountToDelete.id}
              </span>{' '}
              removes it from the copier, deletes its session file, disables any mappings that use
              it, and stops any running workers for it. Existing message logs are kept.
              {deleteMutation.isError && (
                <span className="mt-3 block text-sm text-red-700 dark:text-red-400" role="alert">
                  {errorMessage(deleteMutation.error, 'Deleting the account failed. Try again.')}
                </span>
              )}
            </>
          }
          confirmLabel="Delete account"
          variant="danger"
          icon={<Trash2 className="h-5 w-5" />}
          onConfirm={() => deleteMutation.mutate(accountToDelete.id)}
          onCancel={() => setAccountToDelete(null)}
          isPending={deleteMutation.isPending}
        />
      )}

      {isError ? (
        <ErrorState
          title="We couldn't load your accounts"
          error={error}
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <TableSkeleton columns={5} />
      ) : (
        <TableShell
          caption="Telegram accounts"
          footer={
            accounts.length === 0 ? (
              <EmptyState
                icon={Smartphone}
                title="No Telegram accounts yet"
                description="Connect an account so the copier can read your source channels."
                action={
                  <Button icon={Plus} size="sm" onClick={() => setShowAdd(true)}>
                    Add Account
                  </Button>
                }
              />
            ) : (
              data && (
                <Pagination
                  page={data.page}
                  pageSize={data.page_size}
                  total={data.total}
                  totalPages={data.total_pages}
                  onPageChange={setPage}
                  onPageSizeChange={(n) => {
                    setPageSize(n);
                    setPage(1);
                  }}
                />
              )
            )
          }
        >
          <Thead>
            <tr>
              <SortableTh label="ID" sortKey="id" {...sortProps} />
              <SortableTh label="Name" sortKey="name" {...sortProps} />
              <SortableTh label="Type" sortKey="type" {...sortProps} />
              <SortableTh label="Status" sortKey="status" {...sortProps} />
              <Th className="w-32 text-right">Actions</Th>
            </tr>
          </Thead>
          <Tbody>
            {accounts.map((acc) => (
              <Tr key={acc.id}>
                <Td className="tabular-nums text-ink-subtle">{acc.id}</Td>
                <Td className="font-medium">{acc.name || `Account ${acc.id}`}</Td>
                <Td>
                  <AccountTypeBadge type={acc.type} />
                </Td>
                <Td>
                  <AccountStatusBadge status={acc.status} />
                </Td>
                <Td className="text-right">
                  <AccountTableActions
                    onEdit={() => setEditingAccount(acc)}
                    onView={() => setViewingAccountId(acc.id)}
                    onDelete={() => setAccountToDelete(acc)}
                  />
                </Td>
              </Tr>
            ))}
          </Tbody>
        </TableShell>
      )}
    </div>
  );
}
