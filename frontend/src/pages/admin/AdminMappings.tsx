import { Layers, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { EditMappingDialog } from '../../components/EditMappingDialog';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { MappingEnableToggle } from '../../components/MappingEnableToggle';
import { MappingTableActions } from '../../components/MappingTableActions';
import { ChannelCell } from '../../components/ChannelCell';
import { UserFilterSelect } from '../../components/UserFilterSelect';
import { useToast } from '../../components/Toast';
import { PageHeader } from '../../components/PageHeader';
import { Pagination } from '../../components/Pagination';
import { SortableTh } from '../../components/SortableTh';
import { TableSkeleton } from '../../components/Skeleton';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { TableShell, Tbody, Td, Th, Thead, Tr } from '../../components/ui/TableShell';

type Mapping = {
  id: number;
  user_id: number;
  source_chat_id: number;
  dest_chat_id: number;
  name: string | null;
  source_chat_title?: string | null;
  dest_chat_title?: string | null;
  enabled: boolean;
  schedule_summary?: string;
};

type User = { id: number; email: string; name: string | null };
type PaginatedMappings = { items: Mapping[]; total: number; page: number; page_size: number; total_pages: number };
type PaginatedUsers = { items: User[]; total: number };

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

  const { data, isLoading, isError, error, refetch } = useQuery({
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
      showToast('Mapping deleted. Workers are restarting to apply it.', 'success');
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
      showToast('Updating the mapping failed', 'error');
    },
    onSuccess: (_, vars) => {
      showToast(
        (vars.enabled ? 'Mapping enabled' : 'Mapping disabled') +
          '. Workers are restarting to apply it.',
        'success'
      );
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['mappings'] });
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
        title="All Mappings"
        icon={Layers}
        subtitle="View and manage all user channel mappings"
      />

      <UserFilterSelect
        users={users}
        value={userId}
        onChange={(next) => {
          setUserId(next);
          setPage(1);
        }}
        className="mb-4 max-w-80"
      />

      {editingMapping && (
        <EditMappingDialog mapping={editingMapping} onClose={() => setEditingMapping(null)} />
      )}
      {mappingToDelete && (
        <ConfirmDialog
          title="Delete Channel Mapping"
          message={
            <>
              Deleting{' '}
              <span className="font-medium text-ink">
                {mappingToDelete.name || `Mapping ${mappingToDelete.id}`}
              </span>{' '}
              also removes all of its filters and transformations. This cannot be undone.
            </>
          }
          confirmLabel="Delete mapping"
          variant="danger"
          icon={<Trash2 className="h-5 w-5" />}
          onConfirm={() => deleteMutation.mutate(mappingToDelete.id)}
          onCancel={() => setMappingToDelete(null)}
          isPending={deleteMutation.isPending}
        />
      )}

      {isError ? (
        <ErrorState title="We couldn't load the mappings" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton columns={7} />
      ) : (
        <TableShell
          caption="All channel mappings"
          footer={
            mappings.length === 0 ? (
              <EmptyState
                icon={Layers}
                title={userId != null ? 'This user has no mappings' : 'No mappings yet'}
                description={
                  userId != null
                    ? 'Switch the filter back to all users to see the rest.'
                    : 'Mappings created by any user will be listed here.'
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
              <SortableTh label="User" sortKey="user_id" {...sortProps} />
              <SortableTh label="Name" sortKey="name" {...sortProps} />
              <SortableTh label="Source" sortKey="source_chat_id" {...sortProps} />
              <SortableTh label="Destination" sortKey="dest_chat_id" {...sortProps} />
              <SortableTh label="Status" sortKey="enabled" {...sortProps} />
              <Th>Schedule</Th>
              <Th className="w-32 text-right">Actions</Th>
            </tr>
          </Thead>
          <Tbody>
            {mappings.map((m) => (
              <Tr key={m.id}>
                <Td className="tabular-nums text-ink-subtle">{m.user_id}</Td>
                <Td className="font-medium">{m.name || `Mapping ${m.id}`}</Td>
                <Td className="max-w-56">
                  <ChannelCell title={m.source_chat_title} id={m.source_chat_id} />
                </Td>
                <Td className="max-w-56">
                  <ChannelCell title={m.dest_chat_title} id={m.dest_chat_id} />
                </Td>
                <Td>
                  <MappingEnableToggle
                    enabled={m.enabled}
                    onToggle={() => enableMutation.mutate({ id: m.id, enabled: !m.enabled })}
                    isPending={enableMutation.isPending && enableMutation.variables?.id === m.id}
                  />
                </Td>
                <Td className="text-ink-muted">{m.schedule_summary ?? '24/7'}</Td>
                <Td className="text-right">
                  <MappingTableActions
                    mappingId={m.id}
                    onEdit={() => setEditingMapping(m)}
                    onDelete={() => setMappingToDelete(m)}
                    viewBasePath="/admin/mappings"
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
