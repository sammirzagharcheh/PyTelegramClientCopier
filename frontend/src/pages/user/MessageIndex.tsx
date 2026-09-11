import { Database } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { useAuth } from '../../store/AuthContext';
import { PageHeader } from '../../components/PageHeader';
import { Pagination } from '../../components/Pagination';
import { TableSkeleton } from '../../components/Skeleton';
import { EmptyState, ErrorState } from '../../components/ui/States';
import { TableShell, Tbody, Td, Th, Thead, Tr } from '../../components/ui/TableShell';

type IndexEntry = {
  user_id: number;
  source_chat_id: number;
  source_msg_id: number;
  dest_chat_id: number;
  dest_msg_id: number;
};

type PaginatedIndex = { items: IndexEntry[]; total: number; page: number; page_size: number; total_pages: number };

export function MessageIndex() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['message-index', page, pageSize, user?.id],
    queryFn: async () => (await api.get<PaginatedIndex>(`/message-index?page=${page}&page_size=${pageSize}`)).data,
    enabled: user != null,
  });

  const rawItems = (data?.items ?? []) as IndexEntry[];
  const items =
    user?.role !== 'admin' && user?.id != null
      ? rawItems.filter((e) => Number(e.user_id) === Number(user.id))
      : rawItems;

  return (
    <div>
      <PageHeader
        title="Message Index"
        icon={Database}
        subtitle="Maps source message IDs to destination message IDs for reply threading"
      />

      {isError ? (
        <ErrorState title="We couldn't load the message index" error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <TableSkeleton columns={4} rows={8} />
      ) : (
        <TableShell
          caption="Source to destination message IDs"
          footer={
            items.length === 0 ? (
              <EmptyState
                icon={Database}
                title="No index entries yet"
                description="Entries are written as messages are copied, so replies can be threaded to the right message."
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
              <Th>Source chat</Th>
              <Th>Source message</Th>
              <Th>Destination chat</Th>
              <Th>Destination message</Th>
            </tr>
          </Thead>
          <Tbody>
            {items.map((e, i) => (
              <Tr key={`${e.source_chat_id}-${e.source_msg_id}-${i}`}>
                <Td className="font-mono text-xs tabular-nums">{e.source_chat_id}</Td>
                <Td className="font-mono text-xs tabular-nums">{e.source_msg_id}</Td>
                <Td className="font-mono text-xs tabular-nums">{e.dest_chat_id}</Td>
                <Td className="font-mono text-xs tabular-nums">{e.dest_msg_id}</Td>
              </Tr>
            ))}
          </Tbody>
        </TableShell>
      )}
    </div>
  );
}
