import { MessageSquare } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { formatLocalDateTime } from '../../lib/formatDateTime';
import { useAuth } from '../../store/AuthContext';
import { PageHeader } from '../../components/PageHeader';
import { Pagination } from '../../components/Pagination';
import { StatusBadge } from '../../components/StatusBadge';
import { TableSkeleton } from '../../components/Skeleton';
import { MessageRef } from '../../components/MessageRef';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { Select } from '../../components/ui/Field';
import { TableShell, Tbody, Td, Th, Thead, Tr } from '../../components/ui/TableShell';

type Log = {
  user_id: number;
  mapping_id?: number | null;
  source_chat_id: number;
  source_msg_id: number;
  dest_chat_id: number;
  dest_msg_id: number | null;
  source_chat_title?: string | null;
  dest_chat_title?: string | null;
  timestamp: string;
  status: string;
  skip_reason?: string | null;
  skip_detail?: string | null;
};

type PaginatedLogs = { items: Log[]; total: number; page: number; page_size: number; total_pages: number };

type StatusFilter = '' | 'copied' | 'skipped' | 'failed';

export function Logs() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['message-logs', page, pageSize, statusFilter, user?.id],
    queryFn: async () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (statusFilter) params.set('status', statusFilter);
      return (await api.get<PaginatedLogs>(`/message-logs?${params}`)).data;
    },
    enabled: user != null,
  });

  const rawItems = (data?.items ?? []) as Log[];
  const items =
    user?.role !== 'admin' && user?.id != null
      ? rawItems.filter((log) => Number(log.user_id) === Number(user.id))
      : rawItems;

  return (
    <div>
      <PageHeader
        title="Message Logs"
        icon={MessageSquare}
        subtitle="Copied and skipped message history"
        actions={
          <label className="flex items-center gap-2 text-sm text-ink-muted">
            <span className="whitespace-nowrap">Status</span>
            <Select
              aria-label="Filter by status"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as StatusFilter);
                setPage(1);
              }}
            >
              <option value="">All</option>
              <option value="copied">Copied</option>
              <option value="skipped">Skipped</option>
              <option value="failed">Failed</option>
            </Select>
          </label>
        }
      />

      {isError ? (
        <ErrorState title="We couldn't load your message logs" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton columns={5} rows={8} />
      ) : (
        <TableShell
          caption="Forwarded and skipped messages"
          footer={
            items.length === 0 ? (
              <EmptyState
                icon={MessageSquare}
                title="No messages yet"
                description="Copied and skipped messages appear here once a worker is running and a mapping is enabled."
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
              <Th>Source</Th>
              <Th>Destination</Th>
              <Th>Time</Th>
              <Th>Status</Th>
              <Th>Reason</Th>
            </tr>
          </Thead>
          <Tbody>
            {items.map((log, i) => (
              <Tr key={`${log.source_chat_id}-${log.source_msg_id}-${i}`}>
                <Td className="max-w-56">
                  <MessageRef
                    title={log.source_chat_title}
                    chatId={log.source_chat_id}
                    messageId={log.source_msg_id}
                  />
                </Td>
                <Td className="max-w-56">
                  <MessageRef
                    title={log.dest_chat_title}
                    chatId={log.dest_chat_id}
                    messageId={log.dest_msg_id ?? undefined}
                  />
                </Td>
                <Td className="whitespace-nowrap text-ink-muted">
                  <time dateTime={log.timestamp}>
                    {formatLocalDateTime(log.timestamp, user?.timezone ?? undefined)}
                  </time>
                </Td>
                <Td>
                  <StatusBadge status={log.status ?? ''} variant="status" />
                </Td>
                <Td className="max-w-48 text-sm text-ink-muted">
                  {log.skip_reason
                    ? `${log.skip_reason}${log.skip_detail ? ` · ${log.skip_detail}` : ''}`
                    : '—'}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </TableShell>
      )}
    </div>
  );
}
