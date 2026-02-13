import { Filter, Inbox, Layers, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { EditMappingDialog } from '../../components/EditMappingDialog';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { MappingEnableToggle } from '../../components/MappingEnableToggle';
import { MappingTableActions } from '../../components/MappingTableActions';
import { useToast } from '../../components/Toast';
import { PageHeader } from '../../components/PageHeader';
import { Pagination } from '../../components/Pagination';
import { SortableTh } from '../../components/SortableTh';

type Mapping = {
  id: number;
  user_id: number;
  source_chat_id: number;
  dest_chat_id: number;
  name: string | null;
  source_chat_title?: string | null;
  dest_chat_title?: string | null;
  enabled: boolean;
};

type User = { id: number; email: string; name: string | null };
type PaginatedMappings = { items: Mapping[]; total: number; page: number; page_size: number; total_pages: number };
type PaginatedUsers = { items: User[]; total: number };

function formatChannelLabel(m: Mapping, type: 'source' | 'dest') {
  const title = type === 'source' ? m.source_chat_title : m.dest_chat_title;
  const id = type === 'source' ? m.source_chat_id : m.dest_chat_id;
  return title ? `${title} (${id})` : String(id);
}

export function AdminMappings() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [userId, setUserId] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<string>('id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [editingMapping, setEditingMapping] = useState<Mapping | null>(null);
  const [mappingToDelete, setMappingToDelete] = useState<Mapping | null>(null);
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();

  const { data: usersData } = useQuery({
    queryKey: ['admin', 'users', 'list'],
    queryFn: async () => (await api.get<PaginatedUsers>(`/admin/users?page=1&page_size=100`)).data,
    staleTime: 5 * 60 * 1000,
  });
  const users = usersData?.items ?? [];

  const { data, isLoading } = useQuery({
    queryKey: ['mappings', page, pageSize, userId, sortBy, sortOrder],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), sort_by: sortBy, sort_order: sortOrder });
      if (userId != null) params.set('user_id', String(userId));
      return (await api.get<PaginatedMappings>(`/mappings?${params}`)).data;
    },
  });
  const mappings = data?.items ?? [];

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/mappings/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
      setMappingToDelete(null);
      showToast('Mapping deleted. Workers restarting to apply changes.');
    },
  });

  const enableMutation = useMutation({
    mutationFn: async ({ id, enabled }: { id: number; enabled: boolean }) => {
      return (await api.patch(`/mappings/${id}`, { enabled })).data;
    },
    onMutate: async ({ id, enabled }) => {
      await queryClient.cancelQueries({ queryKey: ['mappings'] });
      const prev = queryClient.getQueryData<PaginatedMappings>([
        'mappings',
        page,
        pageSize,
        userId,
        sortBy,
        sortOrder,
      ]);
      if (prev) {
        queryClient.setQueryData(
          ['mappings', page, pageSize, userId, sortBy, sortOrder],
          {
            ...prev,
            items: prev.items.map((m) => (m.id === id ? { ...m, enabled } : m)),
          }
        );
      }
      return { prev };
    },
    onError: (_err, _vars, context) => {
      if (context?.prev) {
        queryClient.setQueryData(
          ['mappings', page, pageSize, userId, sortBy, sortOrder],
          context.prev
        );
      }
      showToast('Failed to update mapping');
    },
    onSuccess: (_, vars) => {
      showToast(
        (vars.enabled ? 'Mapping enabled' : 'Mapping disabled') + '. Workers restarting to apply changes.'
      );
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
    },
  });

  if (isLoading) return <div className="animate-pulse h-32 bg-gray-200 dark:bg-gray-700 rounded" />;

  return (
    <div>
      <PageHeader
        title="All Mappings"
        icon={Layers}
        subtitle="View and manage all user channel mappings"
      />
      <div className="mb-6 flex flex-wrap items-center gap-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50 px-4 py-3">
        <Filter className="h-4 w-4 text-gray-500 dark:text-gray-400" />
        <label htmlFor="admin-mappings-user-filter" className="text-sm font-medium">Filter by user</label>
        <select
          id="admin-mappings-user-filter"
          value={userId ?? ''}
          onChange={(e) => {
            const v = e.target.value;
            setUserId(v === '' ? null : parseInt(v, 10));
            setPage(1);
          }}
          className="px-3 py-2 rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700"
        >
          <option value="">All users</option>
          {users.map((u) => (
            <option key={u.id} value={u.id}>
              User {u.id} ({u.email})
            </option>
          ))}
        </select>
      </div>
      {editingMapping && (
        <EditMappingDialog mapping={editingMapping} onClose={() => setEditingMapping(null)} />
      )}
      {mappingToDelete && (
        <ConfirmDialog
          title="Delete Channel Mapping"
          message={
            <>
              Are you sure you want to delete the mapping{' '}
              <span className="font-semibold">{mappingToDelete.name || `Mapping ${mappingToDelete.id}`}</span>?
              This will also remove all associated filters. This action cannot be undone.
            </>
          }
          confirmLabel="Delete mapping"
          variant="danger"
          icon={<Trash2 className="h-5 w-5 text-red-600" />}
          onConfirm={() => deleteMutation.mutate(mappingToDelete.id)}
          onCancel={() => setMappingToDelete(null)}
          isPending={deleteMutation.isPending}
        />
      )}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden transition-shadow hover:shadow-lg">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <SortableTh label="User" sortKey="user_id" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Name" sortKey="name" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Source" sortKey="source_chat_id" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Dest" sortKey="dest_chat_id" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <SortableTh label="Status" sortKey="enabled" currentSort={sortBy} currentOrder={sortOrder} onSort={(k, o) => { setSortBy(k); setSortOrder(o); setPage(1); }} />
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase w-32 min-w-[120px]">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {mappings.map((m) => (
              <tr key={m.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                <td className="px-6 py-4 text-sm">{m.user_id}</td>
                <td className="px-6 py-4 text-sm">{m.name || `Mapping ${m.id}`}</td>
                <td className="px-6 py-4 text-sm font-mono" title={`ID: ${m.source_chat_id}`}>
                  {formatChannelLabel(m, 'source')}
                </td>
                <td className="px-6 py-4 text-sm font-mono" title={`ID: ${m.dest_chat_id}`}>
                  {formatChannelLabel(m, 'dest')}
                </td>
                <td className="px-6 py-4 text-sm">
                  <MappingEnableToggle
                    enabled={m.enabled}
                    onToggle={() => enableMutation.mutate({ id: m.id, enabled: !m.enabled })}
                    isPending={enableMutation.isPending && enableMutation.variables?.id === m.id}
                  />
                </td>
                <td className="px-6 py-4 text-sm text-right">
                  <MappingTableActions
                    mappingId={m.id}
                    onEdit={() => setEditingMapping(m)}
                    onDelete={() => setMappingToDelete(m)}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {mappings.length === 0 && (
          <div className="p-8 text-center text-gray-500 flex flex-col items-center gap-2">
            <Inbox className="h-12 w-12 text-gray-400" />
            <p>No mappings yet.</p>
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
