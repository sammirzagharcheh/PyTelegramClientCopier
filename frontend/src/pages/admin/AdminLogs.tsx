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
import { UserFilterSelect } from '../../components/UserFilterSelect';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { TableShell, Tbody, Td, Th, Thead, Tr } from '../../components/ui/TableShell';

type Log = {
  user_id: number;
  source_chat_id: number;
  source_msg_id: number;
  dest_chat_id: number;
  dest_msg_id: number;
  source_chat_title?: string | null;
  dest_chat_title?: string | null;
  timestamp: string;
  status: string;
};

type User = { id: number; email: string; name: string | null };
type PaginatedLogs = { items: Log[]; total: number; page: number; page_size: number; total_pages: number };
type PaginatedUsers = { items: User[]; total: number };

export function AdminLogs() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [userId, setUserId] = useState<number | null>(null);

  const { data: usersData } = useQuery({
    queryKey: ['admin', 'users', 'list'],
    queryFn: async () => (await api.get<PaginatedUsers>(`/admin/users?page=1&page_size=100`)).data,
    staleTime: 5 * 60 * 1000,
  });
  const users = usersData?.items ?? [];

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['admin', 'message-logs', page, pageSize, userId],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (userId != null) params.set('user_id', String(userId));
      return (await api.get<PaginatedLogs>(`/message-logs?${params}`)).data;
    },
  });

  const items = (data?.items ?? []) as Log[];

  return (
    <div>
      <PageHeader
        title="All Message Logs"
        icon={MessageSquare}
        subtitle="Forwarded message history across all users"
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

      {isError ? (
        <ErrorState
          title="We couldn't load the message logs"
          error={error}
          onRetry={() => refetch()}
        />
      ) : isLoading ? (
        <TableSkeleton columns={5} rows={8} />
      ) : (
        <TableShell
          caption="Message logs for all users"
          footer={
            items.length === 0 ? (
              <EmptyState
                icon={MessageSquare}
                title={userId != null ? 'This user has no message logs' : 'No messages copied yet'}
                description={
                  userId != null
                    ? 'Switch the filter back to all users to see the rest.'
                    : 'Copied messages from every mapping will appear here. If this stays empty, check that MongoDB is configured in Settings.'
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
              <Th>User</Th>
              <Th>Source</Th>
              <Th>Destination</Th>
              <Th>Time</Th>
              <Th>Status</Th>
            </tr>
          </Thead>
          <Tbody>
            {items.map((log, i) => (
              <Tr key={`${log.user_id}-${log.source_chat_id}-${log.source_msg_id}-${i}`}>
                <Td className="tabular-nums text-ink-subtle">{log.user_id}</Td>
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
                    messageId={log.dest_msg_id}
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
              </Tr>
            ))}
          </Tbody>
        </TableShell>
      )}
    </div>
  );
}
