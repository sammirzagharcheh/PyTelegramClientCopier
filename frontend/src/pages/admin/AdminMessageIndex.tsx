import { Database } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { PageHeader } from '../../components/PageHeader';
import { Pagination } from '../../components/Pagination';
import { TableSkeleton } from '../../components/Skeleton';
import { UserFilterSelect } from '../../components/UserFilterSelect';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { TableShell, Tbody, Td, Th, Thead, Tr } from '../../components/ui/TableShell';

type IndexEntry = {
  user_id: number;
  source_chat_id: number;
  source_msg_id: number;
  dest_chat_id: number;
  dest_msg_id: number;
};

type User = { id: number; email: string; name: string | null };
type PaginatedIndex = { items: IndexEntry[]; total: number; page: number; page_size: number; total_pages: number };
type PaginatedUsers = { items: User[]; total: number };

export function AdminMessageIndex() {
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
    queryKey: ['admin', 'message-index', page, pageSize, userId],
    queryFn: async () => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (userId != null) params.set('user_id', String(userId));
      return (await api.get<PaginatedIndex>(`/message-index?${params}`)).data;
    },
  });

  const items = (data?.items ?? []) as IndexEntry[];

  return (
    <div>
      <PageHeader
        title="Message Index (All Users)"
        icon={Database}
        subtitle="Source to destination message ID mapping for reply threading"
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
        <ErrorState title="We couldn't load the message index" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton columns={3} rows={8} />
      ) : (
        <TableShell
          caption="Message index for all users"
          footer={
            items.length === 0 ? (
              <EmptyState
                icon={Database}
                title={userId != null ? 'This user has no index entries' : 'No index entries yet'}
                description={
                  userId != null
                    ? 'Switch the filter back to all users to see the rest.'
                    : 'Entries are written as messages are copied, so replies can be threaded to the right message.'
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
            </tr>
          </Thead>
          <Tbody>
            {items.map((e, i) => (
              <Tr key={`${e.user_id}-${e.source_chat_id}-${e.source_msg_id}-${i}`}>
                <Td className="tabular-nums text-ink-subtle">{e.user_id}</Td>
                <Td className="font-mono text-xs tabular-nums">
                  {e.source_chat_id} / {e.source_msg_id}
                </Td>
                <Td className="font-mono text-xs tabular-nums">
                  {e.dest_chat_id} / {e.dest_msg_id}
                </Td>
              </Tr>
            ))}
          </Tbody>
        </TableShell>
      )}
    </div>
  );
}
