import { GitBranch, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { coerceChannelMappingForEdit } from '../../lib/channelMappingDefaults';
import { useActiveAccounts, formatAccountLabel } from '../../hooks/useActiveAccounts';
import { AddMappingDialog } from '../../components/AddMappingDialog';
import { EditMappingDialog } from '../../components/EditMappingDialog';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { MappingEnableToggle } from '../../components/MappingEnableToggle';
import { MappingTableActions } from '../../components/MappingTableActions';
import { ChannelCell } from '../../components/ChannelCell';
import { useToast } from '../../components/Toast';
import { PageHeader } from '../../components/PageHeader';
import { SortableTh } from '../../components/SortableTh';
import { Pagination } from '../../components/Pagination';
import { TableSkeleton } from '../../components/Skeleton';
import { Button } from '../../components/ui/Button';
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
  telegram_account_id?: number | null;
  schedule_summary?: string;
  copy_webhook_payload_template?: string | null;
  copy_webhook_secret_header_name?: string | null;
  copy_webhook_secret_mode?: string | null;
  webhook_secret_configured?: boolean;
  webhook_secret_header_configured?: boolean;
};

type PaginatedMappings = { items: Mapping[]; total: number; page: number; page_size: number; total_pages: number };

export function Mappings() {
  const [showAdd, setShowAdd] = useState(false);
  const [editingMapping, setEditingMapping] = useState<Mapping | null>(null);
  const [mappingToDelete, setMappingToDelete] = useState<Mapping | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sortBy, setSortBy] = useState<string>('id');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const queryClient = useQueryClient();
  const { show: showToast } = useToast();
  const { data: activeAccounts = [] } = useActiveAccounts();

  const accountNameById = (id: number | null | undefined) => {
    if (id == null) return 'Not set';
    const acc = activeAccounts.find((a) => a.id === id);
    return acc ? formatAccountLabel(acc) : `#${id}`;
  };

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['mappings', page, pageSize, sortBy, sortOrder],
    queryFn: async () =>
      (await api.get<PaginatedMappings>(`/mappings?page=${page}&page_size=${pageSize}&sort_by=${sortBy}&sort_order=${sortOrder}`)).data,
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
        sortBy,
        sortOrder,
      ]);
      if (prev) {
        queryClient.setQueryData(
          ['mappings', page, pageSize, sortBy, sortOrder],
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
        queryClient.setQueryData(['mappings', page, pageSize, sortBy, sortOrder], context.prev);
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
        title="Channel Mappings"
        icon={GitBranch}
        subtitle="Configure source and destination channel connections"
        actions={
          <Button icon={Plus} onClick={() => setShowAdd(true)}>
            Add Mapping
          </Button>
        }
      />
      {showAdd && <AddMappingDialog onClose={() => setShowAdd(false)} />}
      {editingMapping && (
        <EditMappingDialog
          mapping={coerceChannelMappingForEdit(editingMapping)}
          onClose={() => setEditingMapping(null)}
        />
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
        <ErrorState
          title="We couldn't load your mappings"
          error={error}
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <TableSkeleton columns={7} />
      ) : (
        <TableShell
          caption="Channel mappings"
          footer={
            mappings.length === 0 ? (
              <EmptyState
                icon={GitBranch}
                title="No mappings yet"
                description="A mapping links one source channel to one destination channel. Add the first one to start copying."
                action={
                  <Button icon={Plus} size="sm" onClick={() => setShowAdd(true)}>
                    Add Mapping
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
              <SortableTh label="Name" sortKey="name" {...sortProps} />
              <Th>Account</Th>
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
                <Td className="font-medium">{m.name || `Mapping ${m.id}`}</Td>
                <Td className="text-ink-muted">{accountNameById(m.telegram_account_id)}</Td>
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
